import streamlit as st
import pandas as pd
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, date

# --- 1. CONFIG & EMAIL SETTINGS ---
st.set_page_config(page_title="BGA F&A Workflow", layout="wide")

# INPUT YOUR MASTER EMAIL CREDENTIALS HERE
SENDER_EMAIL = "your-admin-email@gmail.com" 
SENDER_PASSWORD = "your-app-password" # Use App Password, not regular password
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# --- 2. DATA UTILITIES ---
USER_DB, TASK_DB, CALENDAR_DB, CLIENT_DB = "users.csv", "database.csv", "calendar.csv", "clients.csv"

def load_data(file, columns):
    if not os.path.exists(file): return pd.DataFrame(columns=columns)
    df = pd.read_csv(file)
    for col in columns:
        if col not in df.columns: df[col] = ""
    return df

def save_data(df, file):
    df.to_csv(file, index=False)

# --- 3. THE EMAIL FIX (Invitation Function) ---
def send_invite_email(recipient_email, recipient_name):
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = recipient_email
        msg['Subject'] = "Invitation to BGA F&A Workflow Portal"

        body = f"""
        Hello {recipient_name},

        You have been invited to join the BGA F&A Workflow Portal.
        
        Login: {recipient_email}
        Temporary Password: welcome123

        Please log in and change your password in 'My Profile'.
        """
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, recipient_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        st.error(f"Mail Error: {e}")
        return False

# --- 4. AUTH & SESSION ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("BGA Portal Login")
    u_email = st.text_input("Email").strip().lower()
    u_pass = st.text_input("Password", type="password").strip()
    if st.button("Sign In"):
        if u_email == "admin@thebga.io" and u_pass == "admin123":
            st.session_state.update({"logged_in": True, "user_name": "Admin", "role": "Admin"})
            st.rerun()
        # (Standard login logic follows...)
else:
    user_df = load_data(USER_DB, ["Name", "Email", "Password", "Role", "Manager"])
    task_df = load_data(TASK_DB, ["Date", "Client", "Tower", "Activity", "SOP_Link", "Owner", "Reviewer", "Frequency", "WD_Marker", "Status"])
    client_df = load_data(CLIENT_DB, ["Client_Name"])

    st.sidebar.title("BGA F&A")
    choice = st.sidebar.radio("Navigation", ["📊 Dashboard", "➕ Assign Activity", "🏢 Clients", "👥 Manage Team", "📅 WD Calendar"])

    # --- MANAGE TEAM (WITH EMAIL TRIGGER) ---
    if choice == "👥 Manage Team":
        st.header("Team Management")
        with st.form("user_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            n = col1.text_input("Name")
            e = col2.text_input("Email")
            r = col1.selectbox("Role", ["User", "Manager", "Admin"])
            m = col2.selectbox("Reporting Manager", ["None"] + user_df['Name'].tolist())
            
            if st.form_submit_button("Add Member & Send Invite"):
                if n and e:
                    # 1. Save to Database
                    new_u = pd.DataFrame([{"Name": n, "Email": e, "Role": r, "Manager": m, "Password": "welcome123"}])
                    user_df = pd.concat([user_df, new_u], ignore_index=True)
                    save_data(user_df, USER_DB)
                    
                    # 2. Trigger Real Email
                    with st.spinner("Sending invitation email..."):
                        success = send_invite_email(e, n)
                    
                    if success:
                        st.success(f"Member added and email sent to {e}!")
                    else:
                        st.warning("Member added to database, but email failed. Check your SMTP settings.")
                    st.rerun()

    # --- (Rest of the tabs: Dashboard, Activity, etc., remain exactly as per your latest version) ---
    elif choice == "📊 Dashboard":
        st.header("Operations Dashboard")
        edited_df = st.data_editor(task_df, use_container_width=True)
        if st.button("Save Changes"):
            save_data(edited_df, TASK_DB)
            st.success("Database Updated!")
