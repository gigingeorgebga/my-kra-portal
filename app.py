import streamlit as st
import pandas as pd
import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

# --- 1. CONFIG ---
st.set_page_config(page_title="BGA KRA Management", layout="wide")

# --- 2. GMAIL ENGINE ---
GMAIL_USER = "admin@thebga.io" 
GMAIL_PASSWORD = "xtck srmm ncxx tmhr" 

def send_invite_email(receiver_email, receiver_name):
    app_url = "https://my-team-planner.streamlit.app/" 
    msg = MIMEText(f"Hello {receiver_name},\n\nYou have been invited to the BGA KRA Portal.\n\nLink: {app_url}\nUser: {receiver_email}\nPass: welcome123")
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
TASK_DB = "database.csv"
USER_DB = "users.csv"

def load_data(file, columns):
    if not os.path.exists(file): return pd.DataFrame(columns=columns)
    return pd.read_csv(file)

def save_data(df, file):
    df.to_csv(file, index=False)

# --- 4. SESSION STATE ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

# --- 5. LOGIN ---
if not st.session_state['logged_in']:
    st.header("🔑 BGA Team Login")
    user_df = load_data(USER_DB, ["Name", "Email", "Password", "Role", "Status"])
    u_email = st.text_input("Email").strip().lower()
    u_pass = st.text_input("Password", type="password").strip()
    
    if st.button("Login"):
        if u_email == "admin@thebga.io" and u_pass == "admin123":
            st.session_state.update({"logged_in": True, "user": "Master Admin", "role": "Admin", "email": u_email})
            st.rerun()
        elif not user_df.empty:
            match = user_df[(user_df['Email'].str.lower() == u_email) & (user_df['Password'] == u_pass)]
            if not match.empty:
                st.session_state.update({
                    "logged_in": True, 
                    "user": match.iloc[0]['Name'], 
                    "role": match.iloc[0]['Role'],
                    "email": match.iloc[0]['Email']
                })
                st.rerun()
            else: st.error("Invalid Login")

# --- 6. MAIN APP ---
else:
    task_df = load_data(TASK_DB, ["Date", "Owner", "Task", "Category", "Priority", "Status", "QC_Comments"])
    user_df = load_data(USER_DB, ["Name", "Email", "Password", "Role", "Status"])

    # Sidebar
    try:
        st.sidebar.image("1 BGA Logo Colour.png", use_container_width=True)
    except:
        st.sidebar.title("BGA Portal")

    menu = ["📊 Dashboard", "⚙️ My Settings"]
    if st.session_state['role'] in ["Admin", "Manager"]: menu.append("➕ Assign Activity")
    if st.session_state['role'] == "Admin": menu.append("👥 Manage Team")
    
    choice = st.sidebar.radio("Nav", menu)
    st.sidebar.divider()
    st.sidebar.info(f"User: {st.session_state['user']}\nRole: {st.session_state['role']}")

    # Security Check
    current_pass = user_df[user_df['Email'] == st.session_state['email']]['Password'].values[0] if st.session_state['email'] != "admin@thebga.io" else "admin123"
    if current_pass == "welcome123":
        st.warning("⚠️ Security Alert: You are using the temporary password. Please change it in 'My Settings'.")

    # --- SETTINGS PAGE ---
    if choice == "⚙️ My Settings":
        st.header("⚙️ Account Settings")
        
        # 1. Password Change
        with st.expander("🔐 Change Password"):
            new_pass = st.text_input("Enter New Password", type="password")
            confirm_pass = st.text_input("Confirm New Password", type="password")
            if st.button("Update Password"):
                if new_pass == confirm_pass and len(new_pass) > 4:
                    if st.session_state['email'] == "admin@thebga.io":
                        st.error("Cannot change Master Admin password here. Use GitHub to update the code logic.")
                    else:
                        user_df.loc[user_df['Email'] == st.session_state['email'], 'Password'] = new_pass
                        save_data(user_df, USER_DB)
                        st.success("Password updated successfully!")
                else:
                    st.error("Passwords do not match or are too short.")

        # 2. Profile Pic (Simple visual placeholder)
        with st.expander("🖼️ Profile Picture"):
            pic = st.file_uploader("Upload Picture (PNG/JPG)", type=['png', 'jpg'])
            if pic: st.image(pic, width=150)

    elif choice == "👥 Manage Team":
        st.header("Team & Permissions")
        if not user_df.empty:
            for i, row in user_df.iterrows():
                col_a, col_b, col_c = st.columns([3, 3, 1])
                col_a.write(f"{row['Name']} ({row['Role']})")
                col_b.write(row['Email'])
                if col_c.button("🗑️", key=f"del_{i}"):
                    user_df = user_df.drop(i); save_data(user_df, USER_DB); st.rerun()

        st.subheader("Invite New Member")
        with st.form("invite_form"):
            n, e, r = st.text_input("Name"), st.text_input("Email").strip().lower(), st.selectbox("Role", ["User", "Manager", "Admin"])
            if st.form_submit_button("Send Invite"):
                if e in user_df['Email'].values: st.warning("User exists!")
                else:
                    new_u = pd.DataFrame([{"Name":n, "Email":e, "Password":"welcome123", "Role":r, "Status":"Active"}])
                    save_data(pd.concat([user_df, new_u], ignore_index=True), USER_DB)
                    if send_invite_email(e, n): st.success(f"Invite sent to {e}!")
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
        st.title(f"📊 {st.session_state['user']}'s Portal")
        disp = task_df if st.session_state['role'] in ["Admin", "Manager"] else task_df[task_df['Owner'] == st.session_state['user']]
        upd = st.data_editor(disp, use_container_width=True)
        if st.button("Save Changes"):
            save_data(upd, TASK_DB); st.success("Saved!")

    if st.sidebar.button("Logout"):
        st.session_state['logged_in'] = False
        st.rerun()
