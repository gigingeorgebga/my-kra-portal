import streamlit as st
import pandas as pd
from datetime import datetime
import os
import smtplib
from email.mime.text import MIMEText

# --- 1. CONFIG & LOGO ---
st.set_page_config(page_title="BGA KRA Portal", layout="wide")

try:
    # Using your exact logo name
    st.sidebar.image("1 BGA Logo Colour.png", use_container_width=True)
except:
    st.sidebar.warning("⚠️ Logo not found.")
st.sidebar.divider()

# --- 2. GMAIL SETTINGS ---
GMAIL_USER = "admin@thebga.io" 
GMAIL_PASSWORD = "your-16-char-code-here" # <--- ENSURE THIS IS UPDATED

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
    except:
        return False

# --- 3. DATABASE FUNCTIONS ---
TASK_DB = "database.csv"
USER_DB = "users.csv"

def load_data(file, columns):
    if os.path.exists(file):
        try:
            return pd.read_csv(file)
        except:
            return pd.DataFrame(columns=columns)
    return pd.DataFrame(columns=columns)

def save_data(df, file):
    df.to_csv(file, index=False)

# --- 4. SESSION STATE (The Safety Shield) ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user' not in st.session_state:
    st.session_state['user'] = ""
if 'role' not in st.session_state:
    st.session_state['role'] = "User" # Default role to prevent crash

# --- 5. LOGIN PAGE ---
if not st.session_state['logged_in']:
    st.header("🔑 BGA Team Login")
    user_df = load_data(USER_DB, ["Name", "Email", "Password", "Role", "Status"])
    
    with st.form("login"):
        u_email = st.text_input("Email").strip().lower()
        u_pass = st.text_input("Password", type="password").strip()
        if st.form_submit_button("Login"):
            # HARDCODED ADMIN CHECK
            if u_email == "admin@bga.com" and u_pass == "admin123":
                st.session_state['logged_in'] = True
                st.session_state['user'] = "Admin"
                st.session_state['role'] = "Admin"
                st.rerun()
            # DATABASE USER CHECK
            elif not user_df.empty:
                match = user_df[(user_df['Email'].str.lower() == u_email) & (user_df['Password'] == u_pass)]
                if not match.empty:
                    st.session_state['logged_in'] = True
                    st.session_state['user'] = match.iloc[0]['Name']
                    st.session_state['role'] = match.iloc[0]['Role']
                    st.rerun()
            st.error("Invalid Credentials")

# --- 6. THE DASHBOARD ---
else:
    task_df = load_data(TASK_DB, ["Date", "Owner", "Task", "Type", "Status", "QC_Comments"])
    
    # Sidebar Menu
    menu_options = ["Dashboard", "My Tasks"]
    if st.session_state['role'] == "Admin":
        menu_options.append("Manage Team")
    
    choice = st.sidebar.radio("Navigation", menu_options)

    if choice == "Manage Team":
        st.header("👥 Team Management")
        with st.form("invite_user"):
            new_name = st.text_input("Full Name")
            new_email = st.text_input("Email Address").strip().lower()
            if st.form_submit_button("Send Invite"):
                user_df = load_data(USER_DB, ["Name", "Email", "Password", "Role", "Status"])
                # Add to CSV
                new_user = pd.DataFrame([{"Name": new_name, "Email": new_email, "Password": "welcome123", "Role": "User", "Status": "Active"}])
                save_data(pd.concat([user_df, new_user]), USER_DB)
                
                if send_invite_email(new_email, new_name):
                    st.success(f"Invite sent to {new_email}!")
                else:
                    st.warning("User saved, but email failed. Check your App Password!")

    elif choice == "Dashboard":
        st.title(f"📊 {st.session_state['user']}'s Dashboard")
        st.write("Welcome to the BGA Portal. Use the sidebar to navigate.")
        
        # Simple view of all tasks for Admin
        if st.session_state['role'] == "Admin":
            st.dataframe(task_df, use_container_width=True)
        else:
            user_tasks = task_df[task_df['Owner'] == st.session_state['user']]
            st.dataframe(user_tasks, use_container_width=True)

    if st.sidebar.button("Logout"):
        st.session_state['logged_in'] = False
        st.session_state['role'] = "User"
        st.rerun()
