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
    st.sidebar.warning("⚠️ Logo '1 BGA Logo Colour.png' not found.")
st.sidebar.divider()

# --- 2. GMAIL SETTINGS (Keep these updated) ---
GMAIL_USER = "admin@thebga.io" 
GMAIL_PASSWORD = "your-16-character-code" # <--- Paste your code from Google here

def send_invite_email(receiver_email, receiver_name):
    msg = MIMEText(f"Hello {receiver_name},\n\nYou have been invited to the BGA KRA Portal.\n\nLogin: {receiver_email}\nTemp Password: welcome123\n\nPlease log in and change your password immediately.")
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

# --- 4. SESSION STATE (The Memory) ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user' not in st.session_state:
    st.session_state['user'] = ""
if 'role' not in st.session_state:
    st.session_state['role'] = "User"

# --- 5. LOGIN PAGE ---
if not st.session_state['logged_in']:
    st.header("🔑 BGA Team Login")
    user_df = load_data(USER_DB, ["Name", "Email", "Password", "Role", "Status"])
    
    with st.form("login_form"):
        u_email = st.text_input("Email").strip().lower()
        u_pass = st.text_input("Password", type="password").strip()
        if st.form_submit_button("Login"):
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
                    st.session_state['logged_in'] = True
                    st.session_state['user'] = match.iloc[0]['Name']
                    st.session_state['role'] = match.iloc[0]['Role']
                    st.rerun()
            st.error("Invalid Credentials")

# --- 6. THE MAIN PORTAL ---
else:
    task_df = load_data(TASK_DB, ["Date", "Owner", "Task", "Type", "Status", "QC_Comments"])
    
    # Sidebar Navigation
    menu_options = ["📊 Dashboard"]
    if st.session_state['role'] == "Admin":
        menu_options.append("👥 Manage Team")
    
    choice = st.sidebar.radio("Navigation", menu_options)

    # A. MANAGE TEAM PAGE
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
                    st.warning("User saved to list, but email failed. Check your Gmail settings!")

    # B. DASHBOARD PAGE
    else:
        st.title(f"📊 {st.session_state['user']}'s Dashboard")
        
        # Simple Stats
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Activities", len(task_df))
        col2.metric("Your Pending", len(task_df[(task_df['Owner'] == st.session_state['user']) & (task_df['Status'].str.contains("🔴", na=False))]))
        col3.metric("Role", st.session_state['role'])

        st.divider()

        # The Interactive Table
        st.subheader("📝 Activity Tracker")
        
        # Logic: Admin sees all, Users see only their own rows
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
                    required=True,
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
                # Update only user-specific rows back into the main database
                task_df.update(updated_df)
                save_data(task_df, TASK_DB)
            st.success("Changes saved successfully!")
            st.rerun()

    # Logout Button at the bottom of sidebar
    if st.sidebar.button("🚪 Logout"):
        st.session_state['logged_in'] = False
        st.rerun()
