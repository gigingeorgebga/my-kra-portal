import streamlit as st
import pandas as pd
import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, date
import base64

# --- 1. CONFIG ---
st.set_page_config(page_title="BGA F&A Workflow", layout="wide")

# --- 2. DATABASE FILES ---
USER_DB = "users.csv"
TASK_DB = "database.csv"
CALENDAR_DB = "calendar.csv"
CLIENT_DB = "clients.csv"

def load_data(file, columns):
    if not os.path.exists(file): return pd.DataFrame(columns=columns)
    try:
        df = pd.read_csv(file)
        # Ensure all required columns exist (Migration Support)
        for col in columns:
            if col not in df.columns: df[col] = ""
        return df
    except: return pd.DataFrame(columns=columns)

def save_data(df, file):
    df.to_csv(file, index=False)

# --- 3. WORK DAY (WD) LOGIC ---
def get_current_wd():
    cal_df = load_data(CALENDAR_DB, ["Date", "Is_Holiday"])
    if cal_df.empty: return "WD Not Set"
    
    today_str = date.today().strftime("%Y-%m-%d")
    month_start = date.today().replace(day=1)
    
    # Filter for current month and exclude holidays/weekends
    month_days = cal_df[cal_df['Date'].str.startswith(date.today().strftime("%Y-%m"))]
    working_days = month_days[month_days['Is_Holiday'] == False].sort_values('Date')
    
    wd_count = 0
    for idx, row in working_days.iterrows():
        wd_count += 1
        if row['Date'] == today_str:
            return f"WD {wd_count}"
    return "Holiday/Weekend"

# --- 4. SESSION STATE ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

# --- 5. LOGIN ---
if not st.session_state['logged_in']:
    st.header("🔑 BGA F&A Portal Login")
    user_df = load_data(USER_DB, ["Name", "Email", "Password", "Role", "Manager", "Photo"])
    u_email = st.text_input("Email").strip().lower()
    u_pass = st.text_input("Password", type="password").strip()
    
    if st.button("Login"):
        if u_email == "admin@thebga.io" and u_pass == "admin123":
            st.session_state.update({"logged_in": True, "user_name": "Master Admin", "role": "Admin", "user_email": u_email, "must_change": False})
            st.rerun()
        elif not user_df.empty:
            match = user_df[user_df['Email'].str.lower() == u_email]
            if not match.empty and str(match.iloc[0]['Password']) == u_pass:
                st.session_state.update({"logged_in": True, "user_name": match.iloc[0]['Name'], "role": match.iloc[0]['Role'], "user_email": u_email, "must_change": (u_pass == "welcome123")})
                st.rerun()
            else: st.error("Invalid Credentials")

# --- 6. MAIN APP ---
else:
    user_df = load_data(USER_DB, ["Name", "Email", "Password", "Role", "Manager", "Photo"])
    task_df = load_data(TASK_DB, ["Date", "Client", "Tower", "Activity", "SOP_Link", "Owner", "Reviewer", "Frequency", "WD_Marker", "Start_Time", "End_Time", "Status", "Comments"])
    client_df = load_data(CLIENT_DB, ["Client_Name"])
    
    # Sidebar
    st.sidebar.title("BGA Operations")
    current_wd = get_current_wd()
    st.sidebar.metric("Today's Schedule", current_wd)
    
    menu = ["📊 Dashboard", "👤 My Profile"]
    if st.session_state['role'] in ["Admin", "Manager"]: 
        menu.extend(["➕ Assign Activity", "🏢 Clients"])
    if st.session_state['role'] == "Admin": 
        menu.extend(["👥 Manage Team", "📅 WD Calendar"])
    
    choice = st.sidebar.radio("Navigation", menu)

    # --- A. FORCED PASSWORD CHANGE ---
    if st.session_state.get('must_change'):
        st.warning("🔒 Security: Change your password to unlock the portal.")
        new_p = st.text_input("New Password", type="password")
        if st.button("Update"):
            user_df.loc[user_df['Email'] == st.session_state['user_email'], 'Password'] = new_p
            save_data(user_df, USER_DB)
            st.session_state['must_change'] = False
            st.rerun()
        st.stop()

    # --- B. DASHBOARD ---
    if choice == "📊 Dashboard":
        st.subheader(f"Schedule for {st.session_state['user_name']}")
        
        # Filtering Logic
        if st.session_state['role'] == "Admin":
            view_df = task_df
        elif st.session_state['role'] == "Manager":
            # Managers see their tasks + tasks where they are the Reviewer
            view_df = task_df[(task_df['Owner'] == st.session_state['user_name']) | (task_df['Reviewer'] == st.session_state['user_name'])]
        else:
            # Users see only their assigned tasks
            view_df = task_df[task_df['Owner'] == st.session_state['user_name']]

        # Column Config
        is_user = st.session_state['role'] == "User"
        
        updated_df = st.data_editor(
            view_df,
            column_config={
                "SOP_Link": st.column_config.LinkColumn("SOP"),
                "Status": st.column_config.SelectboxColumn("Status", options=["🔴 Pending", "🟡 In Progress", "🔍 QC Required", "✅ Approved"]),
                "Start_Time": st.column_config.TimeColumn("Start"),
                "End_Time": st.column_config.TimeColumn("End"),
                "Reviewer": st.column_config.SelectboxColumn("Reviewer", options=user_df[user_df['Role'].isin(['Admin', 'Manager'])]['Name'].tolist()),
            },
            use_container_width=True,
            key="main_editor"
        )
        
        if st.button("💾 Save Progress"):
            task_df.update(updated_df)
            save_data(task_df, TASK_DB)
            st.success("Data Synchronized.")

    # --- C. ASSIGN ACTIVITY ---
    elif choice == "➕ Assign Activity":
        st.header("📝 New F&A Task Assignment")
        with st.form("task_form"):
            col1, col2, col3 = st.columns(3)
            client = col1.selectbox("Client", client_df['Client_Name'].tolist() if not client_df.empty else ["Add Clients First"])
            tower = col2.selectbox("Tower", ["O2C", "P2P", "R2R"])
            act = col3.text_input("Activity Name")
            
            sop = col1.text_input("SOP Link (URL)")
            freq = col2.selectbox("Frequency", ["Daily", "Weekly", "Monthly", "Ad-hoc"])
            wd = col3.text_input("WD Marker (e.g., WD 1, WD -1)")
            
            owner = col1.selectbox("Action Owner", user_df['Name'].tolist())
            # Auto-assign Reviewer based on Owner's Default Manager
            default_mgr = user_df[user_df['Name'] == owner]['Manager'].values[0] if not user_df.empty else ""
            reviewer = col2.selectbox("Reporting Manager (Reviewer)", user_df[user_df['Role'].isin(['Admin', 'Manager'])]['Name'].tolist(), index=0)
            
            if st.form_submit_button("Create Task"):
                new_row = pd.DataFrame([{"Date": date.today().strftime("%Y-%m-%d"), "Client": client, "Tower": tower, "Activity": act, 
                                         "SOP_Link": sop, "Owner": owner, "Reviewer": reviewer, "Frequency": freq, "WD_Marker": wd,
                                         "Status": "🔴 Pending"}])
                save_data(pd.concat([task_df, new_row], ignore_index=True), TASK_DB)
                st.success("Task Logged.")

    # --- D. MANAGE TEAM ---
    elif choice == "👥 Manage Team":
        st.header("Team Hierarchy")
        st.dataframe(user_df[["Name", "Email", "Role", "Manager"]], use_container_width=True)
        with st.form("add_user"):
            n = st.text_input("Name")
            e = st.text_input("Email")
            r = st.selectbox("Role", ["User", "Manager", "Admin"])
            m = st.selectbox("Default Reporting Manager", user_df[user_df['Role'].isin(['Admin', 'Manager'])]['Name'].tolist())
            if st.form_submit_button("Add Member"):
                new_u = pd.DataFrame([{"Name":n, "Email":e, "Password":"welcome123", "Role":r, "Manager":m, "Status":"Active"}])
                save_data(pd.concat([user_df, new_u], ignore_index=True), USER_DB)
                st.rerun()

    # --- E. CLIENTS ---
    elif choice == "🏢 Clients":
        st.header("Client Master List")
        new_client = st.text_input("Add New Client Name")
        if st.button("Add Client"):
            new_c_df = pd.DataFrame([{"Client_Name": new_client}])
            save_data(pd.concat([client_df, new_c_df], ignore_index=True), CLIENT_DB)
            st.rerun()
        st.write("Existing Clients:")
        st.table(client_df)

    # --- F. WD CALENDAR ---
    elif choice == "📅 WD Calendar":
        st.header("Working Day Configuration")
        st.info("Mark Holidays/Weekends to calculate WD1, WD2, etc.")
        # Simple bulk generator for current month
        if st.button("Initialize Current Month"):
            import calendar
            year, month = date.today().year, date.today().month
            days_in_month = calendar.monthrange(year, month)[1]
            dates = [date(year, month, d).strftime("%Y-%m-%d") for d in range(1, days_in_month + 1)]
            new_cal = pd.DataFrame({"Date": dates, "Is_Holiday": [False]*len(dates)})
            save_data(new_cal, CALENDAR_DB)
            st.rerun()
        
        cal_data = load_data(CALENDAR_DB, ["Date", "Is_Holiday"])
        edited_cal = st.data_editor(cal_data, use_container_width=True)
        if st.button("Save Calendar"):
            save_data(edited_cal, CALENDAR_DB)
            st.success("Calendar Updated.")

    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()
