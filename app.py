import streamlit as st
import pandas as pd
from datetime import datetime
import os
import smtplib
from email.mime.text import MIMEText

# --- 1. CONFIG & LOGO ---
st.set_page_config(page_title="BGA KRA Portal", layout="wide")

try:
    st.sidebar.image("1 BGA Logo Colour.png", use_container_width=True)
except:
    st.sidebar.warning("⚠️ Logo not found.")
st.sidebar.divider()

# --- 2. GMAIL SETTINGS (Enter your details here) ---
GMAIL_USER = "your-email@gmail.com" # <--- Change to your Gmail
GMAIL_PASSWORD = "your-app-password" # <--- Change to the 16-character code

def send_invite_email(receiver_email, receiver_name):
    msg = MIMEText(f"Hello {receiver_name},\n\nYou have been invited to the BGA KRA Portal. Please log in using your email and the temporary password: welcome123")
    msg['Subject'] = 'Invite: BGA KRA Portal Access'
    msg['From'] = GMAIL_USER
    msg['To'] = receiver_email
    
    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.sendmail(GMAIL_USER, receiver_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        return False

# --- 3. DATABASE FUNCTIONS ---
TASK_DB = "database.csv"
USER_DB = "users.csv"

def load_data(file, columns):
    if os.path.exists(file):
        return pd.read_csv(file)
    return pd.DataFrame(columns=columns)

def save_data(df, file):
    df.to_csv(file, index=False)

# --- 4. LOGIN LOGIC ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.header("🔑 BGA Team Login")
    user_df = load_data(USER_DB, ["Name", "Email", "Password", "Role", "Status"])
    
    with st.form("login"):
        u_email = st.text_input("Email").strip()
        u_pass = st.text_input("Password", type="password").strip()
        if st.form_submit_button("Login"):
            # Hardcoded Admin for first-time setup
            if u_email == "admin@bga.com" and u_pass == "admin123":
                st.session_state['logged_in'] = True
                st.session_state['user'] = "Admin"
                st.session_state['role'] = "Admin"
                st.rerun()
            # Check User Database
            elif not user_df.empty:
                match = user_df[(user_df['Email'] == u_email) & (user_df['Password'] == u_pass)]
                if not match.empty:
                    st.session_state['logged_in'] = True
                    st.session_state['user'] = match.iloc[0]['Name']
                    st.session_state['role'] = match.iloc[0]['Role']
                    st.rerun()
            st.error("Invalid Credentials")

# --- 5. THE PORTAL ---
else:
    task_df = load_data(TASK_DB, ["Date", "Owner", "Task", "Type", "Status", "QC_Comments"])
    
    menu = ["Dashboard", "My Tasks"]
    if st.session_state['role'] == "Admin":
        menu.append("Manage Team")
    
    choice = st.sidebar.radio("Menu", menu)

    if choice == "Manage Team":
        st.header("👥 Team Management")
        with st.form("invite_user"):
            new_name = st.text_input("Full Name (e.g. Arathi Soman)")
            new_email = st.text_input("Email Address")
            if st.form_submit_button("Send Invite"):
                user_df = load_data(USER_DB, ["Name", "Email", "Password", "Role", "Status"])
                new_user = pd.DataFrame([{"Name": new_name, "Email": new_email, "Password": "welcome123", "Role": "User", "Status": "Active"}])
                save_data(pd.concat([user_df, new_user]), USER_DB)
                
                if send_invite_email(new_email, new_name):
                    st.success(f"Invite sent to {new_email}!")
                else:
                    st.warning("User added, but email failed (Check Gmail Settings).")

    elif choice == "Dashboard":
        st.title("📊 BGA Main Dashboard")
        # (Insert the Metrics and Task Table code here...)

    if st.sidebar.button("Logout"):
        st.session_state['logged_in'] = False
        st.rerun()
