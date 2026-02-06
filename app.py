import streamlit as st
import pandas as pd
import os
import smtplib
from email.mime.text import MIMEText

# --- 1. CONFIG ---
st.set_page_config(page_title="BGA KRA Portal", layout="wide")

# This block prevents the app from crashing even if the logo is missing
try:
    if os.path.exists("1 BGA Logo Colour.png"):
        st.sidebar.image("1 BGA Logo Colour.png", use_container_width=True)
    else:
        st.sidebar.title("BGA Portal")
except:
    st.sidebar.title("BGA Portal")

st.sidebar.divider()

# --- 2. GMAIL SETTINGS ---
GMAIL_USER = "admin@thebga.io" 
GMAIL_PASSWORD = "xtck srmm ncxx tmhr" 

def send_invite_email(receiver_email, receiver_name):
    app_url = "https://my-team-planner.streamlit.app/" 
    msg = MIMEText(f"Hello {receiver_name},\n\nInvite: {app_url}\nEmail: {receiver_email}\nPass: welcome123")
    msg['Subject'] = 'BGA KRA Portal Access'
    msg['From'] = GMAIL_USER
    msg['To'] = receiver_email
    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.sendmail(GMAIL_USER, receiver_email, msg.as_string())
        server.quit()
        return True
    except: return False

# --- 3. DATABASE FUNCTIONS (Auto-Creation) ---
TASK_DB = "database.csv"
USER_DB = "users.csv"

def load_data(file, columns):
    if not os.path.exists(file):
        df = pd.DataFrame(columns=columns)
        df.to_csv(file, index=False)
        return df
    try:
        return pd.read_csv(file)
    except:
        return pd.DataFrame(columns=columns)

def save_data(df, file):
    df.to_csv(file, index=False)

# --- 4. SESSION STATE ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'user' not in st.session_state: st.session_state['user'] = ""
if 'role' not in st.session_state: st.session_state['role'] = "User"

# --- 5. LOGIN PAGE ---
if not st.session_state['logged_in']:
    st.header("🔑 BGA Team Login")
    user_df = load_data(USER_DB, ["Name", "Email", "Password", "Role", "Status"])
    
    u_email = st.text_input("Email").strip().lower()
    u_pass = st.text_input("Password", type="password").strip()
    
    if st.button("Login"):
        if u_email == "admin@bga.com" and u_pass == "admin123":
            st.session_state.update({"logged_in": True, "user": "Admin", "role": "Admin"})
            st.rerun()
        elif not user_df.empty:
            match = user_df[(user_df['Email'].str.lower() == u_email) & (user_df['Password'] == u_pass)]
            if not match.empty:
                if u_pass == "welcome123":
                    st.session_state['reset_email'] = u_email
                    st.warning("Please set a new password below.")
                else:
                    st.session_state.update({"logged_in": True, "user": match.iloc[0]['Name'], "role": match.iloc[0]['Role']})
                    st.rerun()
            else: st.error("Invalid Login")

    if 'reset_email' in st.session_state:
        new_p = st.text_input("New Password", type="password")
        if st.button("Save Password"):
            user_df.loc[user_df['Email'] == st.session_state['reset_email'], 'Password'] = new_p
            save_data(user_df, USER_DB)
            st.success("Saved! Log in now.")
            del st.session_state['reset_email']

# --- 6. DASHBOARD ---
else:
    task_df = load_data(TASK_DB, ["Date", "Owner", "Task", "Type", "Status", "QC_Comments"])
    menu = ["📊 Dashboard"]
    if st.session_state['role'] == "Admin": menu.append("👥 Manage Team")
    choice = st.sidebar.radio("Nav", menu)

    if "Manage Team" in choice:
        with st.form("invite"):
            n, e = st.text_input("Name"), st.text_input("Email").strip().lower()
            if st.form_submit_button("Invite"):
                u_df = load_data(USER_DB, ["Name", "Email", "Password", "Role", "Status"])
                new_entry = pd.DataFrame([{"Name":n,"Email":e,"Password":"welcome123","Role":"User","Status":"Active"}])
                save_data(pd.concat([u_df, new_entry], ignore_index=True), USER_DB)
                st.success("Invite Sent!") if send_invite_email(e, n) else st.error("Mail Failed")
    else:
        st.title(f"📊 {st.session_state['user']}'s Portal")
        disp = task_df if st.session_state['role'] == "Admin" else task_df[task_df['Owner'] == st.session_state['user']]
        upd = st.data_editor(disp, use_container_width=True, num_rows="dynamic" if st.session_state['role'] == "Admin" else "fixed")
        if st.button("Save"):
            if st.session_state['role'] == "Admin":
                save_data(upd, TASK_DB)
            else:
                task_df.update(upd)
                save_data(task_df, TASK_DB)
            st.success("Done!")

    if st.sidebar.button("Logout"):
        st.session_state['logged_in'] = False
        st.rerun()
