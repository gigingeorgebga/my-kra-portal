import streamlit as st
import pandas as pd
import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

# --- 1. CONFIG & LOGO ---
st.set_page_config(page_title="BGA KRA Management", layout="wide")

# Force logo check - ensures it doesn't crash the app if missing
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
    user_df = load_data(USER_DB, ["Name", "Email", "Password", "Role", "Status"])
    
    u_email = st.text_input("Email").strip().lower()
    u_pass = st.text_input("Password", type="password").strip()
    
    if st.button("Login"):
        # 1. Master Recovery Login
        if u_email == "admin@thebga.io" and u_pass == "admin123":
            st.session_state.update({"logged_in": True, "user_name": "Master Admin", "role": "Admin", "user_email": u_email})
            st.rerun()
        
        # 2. Database Login
        elif not user_df.empty:
            # Case-insensitive email match
            match = user_df[user_df['Email'].str.lower() == u_email]
            if not match.empty:
                if str(match.iloc[0]['Password']) == u_pass:
                    st.session_state.update({
                        "logged_in": True, 
                        "user_name": match.iloc[0]['Name'], 
                        "role": match.iloc[0]['Role'],
                        "user_email": u_email
                    })
                    st.rerun()
                else:
                    st.error("Incorrect Password.")
            else:
                st.error("Email not found in database.")
        else:
            st.error("Database is empty. Use Master Admin to start.")

# --- 6. MAIN APPLICATION ---
else:
    # Double check session integrity
    if not st.session_state.get('user_email'):
        st.session_state['logged_in'] = False
        st.rerun()

    task_df = load_data(TASK_DB, ["Date", "Owner", "Task", "Category", "Priority", "Status", "QC_Comments"])
    user_df = load_data(USER_DB, ["Name", "Email", "Password", "Role", "Status"])

    # Sidebar Navigation
    menu = ["📊 Dashboard", "⚙️ My Settings"]
    if st.session_state['role'] in ["Admin", "Manager"]: menu.append("➕ Assign Activity")
    if st.session_state['role'] == "Admin": menu.append("👥 Manage Team")
    
    choice = st.sidebar.radio("Navigation", menu)
    st.sidebar.divider()
    st.sidebar.write(f"**User:** {st.session_state['user_name']}")
    st.sidebar.write(f"**Role:** {st.session_state['role']}")

    # --- SETTINGS PAGE ---
    if choice == "⚙️ My Settings":
        st.header("⚙️ Account Settings")
        with st.expander("🔐 Change Password"):
            new_p = st.text_input("New Password", type="password")
            conf_p = st.text_input("Confirm Password", type="password")
            if st.button("Update"):
                if new_p == conf_p and len(new_p) >= 6:
                    if st.session_state['user_email'] == "admin@thebga.io":
                        st.error("Cannot change Master Admin password here.")
                    else:
                        user_df.loc[user_df['Email'] == st.session_state['user_email'], 'Password'] = new_p
                        save_data(user_df, USER_DB)
                        st.success("Password updated!")
                else:
                    st.error("Passwords must match and be 6+ characters.")

    # --- MANAGE TEAM ---
    elif choice == "👥 Manage Team":
        st.header("Team Management")
        st.dataframe(user_df[["Name", "Email", "Role", "Status"]], use_container_width=True)
        
        with st.form("invite"):
            n, e, r = st.text_input("Name"), st.text_input("Email").lower(), st.selectbox("Role", ["User", "Manager", "Admin"])
            if st.form_submit_button("Invite"):
                if e in user_df['Email'].values: st.warning("Already exists!")
                else:
                    new_u = pd.DataFrame([{"Name":n, "Email":e, "Password":"welcome123", "Role":r, "Status":"Active"}])
                    save_data(pd.concat([user_df, new_u], ignore_index=True), USER_DB)
                    send_invite_email(e, n)
                    st.success("Invited!")
                    st.rerun()

    # --- DASHBOARD ---
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
