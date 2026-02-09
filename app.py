import streamlit as st
import pandas as pd
import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import base64

# --- 1. CONFIG & LOGO ---
st.set_page_config(page_title="BGA KRA Management", layout="wide")

# Force logo check
logo_path = "1 BGA Logo Colour.png"
if os.path.exists(logo_path):
    st.sidebar.image(logo_path, use_container_width=True)
else:
    st.sidebar.title("BGA PORTAL")

# --- 2. GMAIL ENGINE ---
GMAIL_USER = "admin@thebga.io" 
GMAIL_PASSWORD = "xtck srmm ncxx tmhr" 

def send_invite_email(receiver_email, receiver_name):
    app_url = "https://my-team-planner.streamlit.app/" 
    msg = MIMEText(f"Hello {receiver_name},\n\nInvite: {app_url}\nUser: {receiver_email}\nPass: welcome123")
    msg['Subject'] = 'Invite: BGA KRA Portal'
    msg['From'] = GMAIL_USER
    msg['To'] = receiver_email
    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.sendmail(GMAIL_USER, receiver_email, msg.as_string())
        server.quit()
        return True
    except: return False

# --- 3. DATABASE ENGINE ---
USER_DB = "users.csv"
TASK_DB = "database.csv"

def load_data(file, columns):
    if not os.path.exists(file): return pd.DataFrame(columns=columns)
    try:
        return pd.read_csv(file)
    except:
        return pd.DataFrame(columns=columns)

def save_data(df, file):
    df.to_csv(file, index=False)

# --- 4. SESSION STATE ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'user_email' not in st.session_state: st.session_state['user_email'] = ""

# --- 5. LOGIN PAGE ---
if not st.session_state['logged_in']:
    st.header("🔑 BGA Team Login")
    user_df = load_data(USER_DB, ["Name", "Email", "Password", "Role", "Status", "Photo"])
    
    u_email = st.text_input("Email").strip().lower()
    u_pass = st.text_input("Password", type="password").strip()
    
    if st.button("Login"):
        if u_email == "admin@thebga.io" and u_pass == "admin123":
            st.session_state.update({"logged_in": True, "user_name": "Master Admin", "role": "Admin", "user_email": u_email, "must_change": False})
            st.rerun()
        elif not user_df.empty:
            match = user_df[user_df['Email'].str.lower() == u_email]
            if not match.empty:
                if str(match.iloc[0]['Password']) == u_pass:
                    must_change = (u_pass == "welcome123")
                    st.session_state.update({
                        "logged_in": True, 
                        "user_name": match.iloc[0]['Name'], 
                        "role": match.iloc[0]['Role'],
                        "user_email": u_email,
                        "must_change": must_change
                    })
                    st.rerun()
                else: st.error("Incorrect Password.")
            else: st.error("Email not found.")
        else: st.error("Database is empty.")

# --- 6. MAIN APPLICATION ---
else:
    user_df = load_data(USER_DB, ["Name", "Email", "Password", "Role", "Status", "Photo"])
    task_df = load_data(TASK_DB, ["Date", "Owner", "Task", "Category", "Priority", "Status", "QC_Comments"])

    # Sidebar Profile Display
    user_row = user_df[user_df['Email'] == st.session_state['user_email']]
    if not user_row.empty and pd.notnull(user_row.iloc[0].get('Photo')):
        try:
            st.sidebar.image(user_row.iloc[0]['Photo'], width=100)
        except: pass

    st.sidebar.write(f"**User:** {st.session_state['user_name']}")
    st.sidebar.write(f"**Role:** {st.session_state['role']}")
    
    # --- A. FORCED PASSWORD CHANGE ---
    if st.session_state.get('must_change'):
        st.warning("🔒 First Time Login: You must change your password before continuing.")
        with st.form("force_change"):
            new_p = st.text_input("New Password", type="password")
            conf_p = st.text_input("Confirm New Password", type="password")
            if st.form_submit_button("Update & Unlock Portal"):
                if new_p == conf_p and len(new_p) >= 6 and new_p != "welcome123":
                    user_df.loc[user_df['Email'] == st.session_state['user_email'], 'Password'] = new_p
                    save_data(user_df, USER_DB)
                    st.session_state['must_change'] = False
                    st.success("Password Updated! Unlocking...")
                    st.rerun()
                else:
                    st.error("Invalid password. Must match, be 6+ chars, and not 'welcome123'.")
        st.stop() # Stops the rest of the app from loading until password changed

    # --- B. NORMAL NAVIGATION ---
    menu = ["📊 Dashboard", "⚙️ My Profile"]
    if st.session_state['role'] in ["Admin", "Manager"]: menu.append("➕ Assign Activity")
    if st.session_state['role'] == "Admin": menu.append("👥 Manage Team")
    choice = st.sidebar.radio("Navigation", menu)
    st.sidebar.divider()

    if choice == "⚙️ My Profile":
        st.header("👤 My Profile Settings")
        
        # 1. Photo Upload
        st.subheader("Profile Photo")
        uploaded_file = st.file_uploader("Upload a photo", type=['png', 'jpg', 'jpeg'])
        if uploaded_file:
            # Convert image to base64 string to store in CSV
            encoded = base64.b64encode(uploaded_file.read()).decode()
            img_data = f"data:image/png;base64,{encoded}"
            if st.button("Save Photo"):
                user_df.loc[user_df['Email'] == st.session_state['user_email'], 'Photo'] = img_data
                save_data(user_df, USER_DB)
                st.success("Photo Saved!")
                st.rerun()

        # 2. Regular Password Change
        st.subheader("Security")
        with st.expander("Change Password"):
            rp_new = st.text_input("New Password", type="password", key="rp_new")
            if st.button("Change Password"):
                if len(rp_new) >= 6:
                    user_df.loc[user_df['Email'] == st.session_state['user_email'], 'Password'] = rp_new
                    save_data(user_df, USER_DB)
                    st.success("Password Updated!")
                else: st.error("Too short!")

    elif choice == "👥 Manage Team":
        st.header("Team Management")
        st.dataframe(user_df[["Name", "Email", "Role", "Status"]], use_container_width=True)
        with st.form("invite"):
            n, e, r = st.text_input("Name"), st.text_input("Email").lower(), st.selectbox("Role", ["User", "Manager", "Admin"])
            if st.form_submit_button("Invite"):
                if e in user_df['Email'].values: st.warning("Exists!")
                else:
                    new_u = pd.DataFrame([{"Name":n, "Email":e, "Password":"welcome123", "Role":r, "Status":"Active", "Photo":""}])
                    save_data(pd.concat([user_df, new_u], ignore_index=True), USER_DB)
                    send_invite_email(e, n)
                    st.success("Invited!")
                    st.rerun()

    elif choice == "➕ Assign Activity":
        st.header("📝 Create Activity")
        with st.form("task_form"):
            t = st.text_input("Task Name")
            c = st.selectbox("Category", ["Operations", "Marketing", "Finance", "HR", "Other"])
            p = st.selectbox("Priority", ["⭐ High", "🟦 Medium", "📉 Low"])
            o = st.selectbox("Assign To", user_df['Name'].tolist())
            if st.form_submit_button("Assign"):
                new_t = pd.DataFrame([{"Date": datetime.now().strftime("%Y-%m-%d"), "Owner":o, "Task":t, "Category":c, "Priority":p, "Status":"🔴 Pending", "QC_Comments":""}])
                save_data(pd.concat([task_df, new_t], ignore_index=True), TASK_DB)
                st.success("Task Assigned!")

    else:
        st.title(f"📊 {st.session_state['user_name']}'s Dashboard")
        is_admin = st.session_state['role'] in ["Admin", "Manager"]
        disp = task_df if is_admin else task_df[task_df['Owner'] == st.session_state['user_name']]
        updated = st.data_editor(disp, use_container_width=True)
        if st.button("Save"):
            save_data(updated, TASK_DB)
            st.success("Saved!")

    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()
