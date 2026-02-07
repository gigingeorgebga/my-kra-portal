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

def send_notification(receiver_email, subject, body):
    msg = MIMEText(body)
    msg['Subject'] = subject
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
    if not os.path.exists(file):
        df = pd.DataFrame(columns=columns)
        df.to_csv(file, index=False)
        return df
    return pd.read_csv(file)

def save_data(df, file):
    df.to_csv(file, index=False)

# --- 4. SESSION STATE ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'user' not in st.session_state: st.session_state['user'] = ""
if 'role' not in st.session_state: st.session_state['role'] = "User"

# --- 5. LOGIN (With Recovery Mode) ---
if not st.session_state['logged_in']:
    st.header("🔑 BGA Team Login")
    user_df = load_data(USER_DB, ["Name", "Email", "Password", "Role", "Status"])
    
    u_email = st.text_input("Email").strip().lower()
    u_pass = st.text_input("Password", type="password").strip()
    
    if st.button("Login"):
        # RECOVERY CHECK: If CSV is empty, allow this specific login to create the first Admin
        if user_df.empty or u_email == "admin@thebga.io":
            if u_pass == "admin123":
                st.session_state.update({"logged_in": True, "user": "Master Admin", "role": "Admin"})
                st.rerun()
        
        # NORMAL CHECK
        elif not user_df.empty:
            match = user_df[(user_df['Email'].str.lower() == u_email) & (user_df['Password'] == u_pass)]
            if not match.empty:
                st.session_state.update({
                    "logged_in": True, 
                    "user": match.iloc[0]['Name'], 
                    "role": match.iloc[0]['Role']
                })
                st.rerun()
            else: st.error("Invalid Credentials")

# --- 6. DASHBOARD & WORKFLOW ---
else:
    task_df = load_data(TASK_DB, ["Date", "Owner", "Task", "Category", "Priority", "Status", "QC_Comments"])
    user_df = load_data(USER_DB, ["Name", "Email", "Role"])
    
    menu = ["📊 Dashboard"]
    if st.session_state['role'] in ["Admin", "Manager"]:
        menu.append("➕ Assign Activity")
    if st.session_state['role'] == "Admin":
        menu.append("👥 Manage Team")
    
    choice = st.sidebar.radio("Navigation", menu)
    st.sidebar.divider()
    st.sidebar.info(f"User: {st.session_state['user']}\nRole: {st.session_state['role']}")

    # --- A. TASK ASSIGNMENT ---
    if choice == "➕ Assign Activity":
        st.header("📝 Create Activity")
        with st.form("new_task"):
            col1, col2 = st.columns(2)
            t_name = col1.text_input("Activity/Task Name")
            t_cat = col2.selectbox("Category", ["Operations", "Marketing", "Finance", "HR", "Sales", "Other"])
            t_prio = col1.selectbox("Priority", ["⭐ High", "🟦 Medium", "📉 Low"])
            
            # Get list of names, add "Master Admin" if list is empty
            names = user_df['Name'].tolist() if not user_df.empty else ["Master Admin"]
            assignee = st.selectbox("Assign To", names)
            
            if st.form_submit_button("Assign Now"):
                new_row = pd.DataFrame([{"Date": datetime.now().strftime("%Y-%m-%d"), 
                                         "Owner": assignee, "Task": t_name, 
                                         "Category": t_cat, "Priority": t_prio,
                                         "Status": "🔴 Pending", "QC_Comments": ""}])
                save_data(pd.concat([task_df, new_row], ignore_index=True), TASK_DB)
                st.success(f"Activity created for {assignee}!")

    # --- B. DASHBOARD ---
    elif choice == "📊 Dashboard":
        st.title(f"📊 {st.session_state['user']}'s Portal")
        
        if st.session_state['role'] in ["Admin", "Manager"]:
            display_df = task_df
        else:
            display_df = task_df[task_df['Owner'] == st.session_state['user']]

        is_staff = st.session_state['role'] == "User"
        
        updated_df = st.data_editor(
            display_df,
            column_config={
                "Status": st.column_config.SelectboxColumn("Status", options=["🔴 Pending", "🟡 In Progress", "🔍 QC Required", "✅ Approved"]),
                "Priority": st.column_config.SelectboxColumn("Priority", options=["⭐ High", "🟦 Medium", "📉 Low"], disabled=is_staff),
                "Category": st.column_config.TextColumn(disabled=is_staff),
                "Task": st.column_config.TextColumn(disabled=is_staff),
                "Owner": st.column_config.TextColumn(disabled=is_staff),
            },
            use_container_width=True,
            num_rows="dynamic" if st.session_state['role'] == "Admin" else "fixed"
        )

        if st.button("💾 Save Changes"):
            save_data(updated_df if st.session_state['role'] in ["Admin", "Manager"] else task_df.update(updated_df) or task_df, TASK_DB)
            st.success("Changes saved!")
            st.rerun()

    # --- C. MANAGE TEAM ---
    elif choice == "👥 Manage Team":
        st.header("Team & Permissions")
        
        # Show Current Users
        if not user_df.empty:
            st.write("Current Team Members:")
            st.dataframe(user_df, use_container_width=True)
        
        with st.form("add_user"):
            name = st.text_input("Name")
            email = st.text_input("Email").lower()
            role = st.selectbox("Role", ["User", "Manager", "Admin"])
            if st.form_submit_button("Create User"):
                u_df = load_data(USER_DB, ["Name", "Email", "Password", "Role", "Status"])
                new_u = pd.DataFrame([{"Name":name, "Email":email, "Password":"welcome123", "Role":role, "Status":"Active"}])
                save_data(pd.concat([u_df, new_u], ignore_index=True), USER_DB)
                st.success(f"Created {role}: {name}. They can now login with 'welcome123'")

    if st.sidebar.button("Logout"):
        st.session_state['logged_in'] = False
        st.rerun()
