import streamlit as st
import pandas as pd
from datetime import datetime
import os
import smtplib
from email.mime.text import MIMEText

# --- 1. CONFIG & LOGO ---
st.set_page_config(page_title="BGA KRA Portal", layout="wide")

try:
    # Using your exact logo name: 1 BGA Logo Colour.png
    st.sidebar.image("1 BGA Logo Colour.png", use_container_width=True)
except:
    st.sidebar.warning("⚠️ Logo '1 BGA Logo Colour.png' not found in GitHub.")
st.sidebar.divider()

# --- 2. GMAIL SETTINGS (Configured with your details) ---
GMAIL_USER = "admin@thebga.io" 
GMAIL_PASSWORD = "xtck srmm ncxx tmhr" 

def send_invite_email(receiver_email, receiver_name):
    # I have updated this with your REAL URL:
    app_url = "https://my-team-planner.streamlit.app/" 
    
    msg = MIMEText(f"Hello {receiver_name},\n\nYou have been invited to the BGA KRA Portal.\n\nLogin Email: {receiver_email}\nTemporary Password: welcome123\n\nPlease log in here: {app_url}\n\nYou will be asked to set a private password upon your first login.")
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

# --- 4. SESSION STATE (Memory) ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user' not in st.session_state:
    st.session_state['user'] = ""
if 'role' not in st.session_state:
    st.session_state['role'] = "User"

# --- 5. LOGIN & REGISTRATION LOGIC ---
if not st.session_state['logged_in']:
    st.header("🔑 BGA Team Login")
    user_df = load_data(USER_DB, ["Name", "Email", "Password", "Role", "Status"])
    
    u_email = st.text_input("Email").strip().lower()
    u_pass = st.text_input("Password", type="password").strip()
    
    if st.button("Login"):
        # ADMIN HARDCODED LOGIN
        if u_email == "admin@bga.com" and u_pass == "admin123":
            st.session_state['logged_in'] = True
            st.session_state['user'] = "Admin"
            st.session_state['role'] = "Admin"
            st.rerun()
        # TEAM MEMBER LOGIN
        elif not user_df.empty:
            match = user_df[(user_df['Email'].str.lower() == u_email) & (user_df['Password'] == u_pass)]
            if not match.empty:
                if u_pass == "welcome123":
                    st.warning("First-time login! Create your private password below.")
                    st.session_state['reset_email'] = u_email
                else:
                    st.session_state['logged_in'] = True
                    st.session_state['user'] = match.iloc[0]['Name']
                    st.session_state['role'] = match.iloc[0]['Role']
                    st.rerun()
            else:
                st.error("Invalid Credentials")

    # Password Reset Section
    if 'reset_email' in st.session_state:
        st.divider()
        new_p = st.text_input("Create New Password", type="password")
        if st.button("Confirm New Password"):
            current_users = load_data(USER_DB, ["Name", "Email", "Password", "Role", "Status"])
            current_users.loc[current_users['Email'] == st.session_state['reset_email'], 'Password'] = new_p
            save_data(current_users, USER_DB)
            st.success("Success! Now login with your new password.")
            del st.session_state['reset_email']

# --- 6. THE MAIN DASHBOARD ---
else:
    task_df = load_data(TASK_DB, ["Date", "Owner", "Task", "Type", "Status", "QC_Comments"])
    
    menu_options = ["📊 Dashboard"]
    if st.session_state['role'] == "Admin":
        menu_options.append("👥 Manage Team")
    
    choice = st.sidebar.radio("Navigation", menu_options)

    if "Manage Team" in choice:
        st.header("👥 Team Management")
        with st.form("invite_user"):
            new_name = st.text_input("Full Name")
            new_email = st.text_input("Email Address").strip().lower()
            if st.form_submit_button("Send Invite"):
                user_df = load_data(USER_DB, ["Name", "Email", "Password", "Role", "Status"])
                new_user = pd.DataFrame([{"Name": new_name, "Email": new_email, "Password": "welcome123", "Role": "User", "Status": "Active"}])
                save_data(pd.concat([user_df, new_user]), USER_DB)
                
                if send_invite_email(new_email, new_name):
                    st.success(f"Invite sent to {new_email}!")
                else:
                    st.error("Email failed. Contact support.")

    else:
        st.title(f"📊 {st.session_state['user']}'s Dashboard")
        
        # Task Table
        if st.session_state['role'] == "Admin":
            display_df = task_df
        else:
            display_df = task_df[task_df['Owner'] == st.session_state['user']]

        updated_df = st.data_editor(
            display_df,
            column_config={
                "Status": st.column_config.SelectboxColumn(
                    "Status",
                    options=["🔴 Pending", "🟡 In Progress", "🟢 Completed", "🔍 QC Required", "✅ Approved"],
                ),
                "Date": st.column_config.TextColumn(disabled=True),
                "Owner": st.column_config.TextColumn(disabled=True) if st.session_state['role'] != "Admin" else st.column_config.SelectboxColumn("Owner", options=["Admin", "Arathi", "Vineeth", "Muaad", "Mili", "Revathy"])
            },
            use_container_width=True,
            num_rows="dynamic" if st.session_state['role'] == "Admin" else "fixed"
        )

        if st.button("💾 Save All Changes"):
            if st.session_state['role'] == "Admin":
                save_data(updated_df, TASK_DB)
            else:
                task_df.update(updated_df)
                save_data(task_df, TASK_DB)
            st.success("Updated!")
            st.rerun()

    if st.sidebar.button("Log Out"):
        st.session_state['logged_in'] = False
        st.rerun()
