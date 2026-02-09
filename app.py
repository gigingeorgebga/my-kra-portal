import streamlit as st
import pandas as pd
import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

# --- 1. CONFIG ---
st.set_page_config(page_title="BGA KRA Management", layout="wide")

try:
    st.sidebar.image("1 BGA Logo Colour.png", use_container_width=True)
except:
    st.sidebar.title("BGA KRA Portal")

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
        # Using a more robust connection method
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.sendmail(GMAIL_USER, receiver_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        st.error(f"Mail Error: {e}")
        return False

# --- 3. DATABASE ENGINE ---
TASK_DB = "database.csv"
USER_DB = "users.csv"

def load_data(file, columns):
    if not os.path.exists(file):
        return pd.DataFrame(columns=columns)
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
        # Fallback for Master Admin
        if u_email == "admin@thebga.io" and u_pass == "admin123":
            st.session_state.update({"logged_in": True, "user": "Master Admin", "role": "Admin"})
            st.rerun()
        elif not user_df.empty:
            match = user_df[(user_df['Email'].str.lower() == u_email) & (user_df['Password'] == u_pass)]
            if not match.empty:
                st.session_state.update({"logged_in": True, "user": match.iloc[0]['Name'], "role": match.iloc[0]['Role']})
                st.rerun()
            else: st.error("Invalid Login")

# --- 6. MAIN APP ---
else:
    task_df = load_data(TASK_DB, ["Date", "Owner", "Task", "Category", "Priority", "Status", "QC_Comments"])
    user_df = load_data(USER_DB, ["Name", "Email", "Password", "Role", "Status"])

    menu = ["📊 Dashboard"]
    if st.session_state['role'] in ["Admin", "Manager"]: menu.append("➕ Assign Activity")
    if st.session_state['role'] == "Admin": menu.append("👥 Manage Team")
    choice = st.sidebar.radio("Nav", menu)

    if choice == "👥 Manage Team":
        st.header("Team & Permissions")
        
        # Display and Delete logic
        if not user_df.empty:
            st.write("Current Team:")
            # Adding a delete feature
            for i, row in user_df.iterrows():
                col_a, col_b, col_c = st.columns([3, 3, 1])
                col_a.write(f"{row['Name']} ({row['Role']})")
                col_b.write(row['Email'])
                if col_c.button("🗑️", key=f"del_{i}"):
                    user_df = user_df.drop(i)
                    save_data(user_df, USER_DB)
                    st.rerun()

        st.divider()
        st.subheader("Invite New Member")
        with st.form("invite_form"):
            n = st.text_input("Full Name")
            e = st.text_input("Email").strip().lower()
            r = st.selectbox("Role", ["User", "Manager", "Admin"])
            if st.form_submit_button("Send Invite"):
                if e in user_df['Email'].values:
                    st.warning("⚠️ This user already exists!")
                else:
                    new_u = pd.DataFrame([{"Name":n, "Email":e, "Password":"welcome123", "Role":r, "Status":"Active"}])
                    user_df = pd.concat([user_df, new_u], ignore_index=True)
                    save_data(user_df, USER_DB)
                    if send_invite_email(e, n):
                        st.success(f"Invite sent to {e}!")
                    else:
                        st.error("User added to list, but email failed. Check spam or Gmail settings.")
                    st.rerun()

    elif choice == "➕ Assign Activity":
        st.header("📝 Create Activity")
        with st.form("task_form"):
            t = st.text_input("Task Name")
            c = st.selectbox("Category", ["Operations", "Marketing", "Finance", "Other"])
            p = st.selectbox("Priority", ["⭐ High", "🟦 Medium", "📉 Low"])
            o = st.selectbox("Assign To", user_df['Name'].tolist() if not user_df.empty else ["Master Admin"])
            if st.form_submit_button("Assign"):
                new_t = pd.DataFrame([{"Date": datetime.now().strftime("%Y-%m-%d"), "Owner":o, "Task":t, "Category":c, "Priority":p, "Status":"🔴 Pending", "QC_Comments":""}])
                save_data(pd.concat([task_df, new_t], ignore_index=True), TASK_DB)
                st.success("Task Assigned!")

    else:
        st.title(f"📊 {st.session_state['user']}'s Portal")
        disp = task_df if st.session_state['role'] in ["Admin", "Manager"] else task_df[task_df['Owner'] == st.session_state['user']]
        upd = st.data_editor(disp, use_container_width=True)
        if st.button("Save Changes"):
            save_data(upd, TASK_DB)
            st.success("Saved!")

    if st.sidebar.button("Logout"):
        st.session_state['logged_in'] = False
        st.rerun()
