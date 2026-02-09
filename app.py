import streamlit as st
import pandas as pd
import os
from datetime import datetime, date

# --- 1. CONFIG (Default Theme) ---
st.set_page_config(page_title="BGA F&A Workflow", layout="wide")

# --- 2. DATA UTILITIES ---
USER_DB, TASK_DB, CALENDAR_DB, CLIENT_DB = "users.csv", "database.csv", "calendar.csv", "clients.csv"

def load_data(file, columns):
    if not os.path.exists(file): 
        return pd.DataFrame(columns=columns)
    try:
        df = pd.read_csv(file)
        # Check and add missing columns automatically
        for col in columns:
            if col not in df.columns: df[col] = ""
        return df
    except: 
        return pd.DataFrame(columns=columns)

def save_data(df, file):
    df.to_csv(file, index=False)

def get_current_wd():
    cal_df = load_data(CALENDAR_DB, ["Date", "Is_Holiday"])
    if cal_df.empty: return "WD Not Set"
    cal_df['Is_Holiday'] = cal_df['Is_Holiday'].astype(str).str.lower() == 'true'
    working_days = cal_df[cal_df['Is_Holiday'] == False].sort_values('Date')
    today_str = date.today().strftime("%Y-%m-%d")
    
    wd_count = 0
    for _, row in working_days.iterrows():
        wd_count += 1
        if row['Date'] == today_str: return f"WD {wd_count}"
    return "Non-Working Day"

# --- 3. AUTHENTICATION ---
if 'logged_in' not in st.session_state: 
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("BGA Portal Login")
    with st.container(border=True):
        u_email = st.text_input("Email").strip().lower()
        u_pass = st.text_input("Password", type="password").strip()
        if st.button("Sign In", use_container_width=True):
            user_df = load_data(USER_DB, ["Name", "Email", "Password", "Role", "Manager"])
            if u_email == "admin@thebga.io" and u_pass == "admin123":
                st.session_state.update({"logged_in": True, "user_name": "Admin", "role": "Admin"})
                st.rerun()
            elif not user_df.empty:
                match = user_df[user_df['Email'].str.lower() == u_email]
                if not match.empty and str(match.iloc[0]['Password']) == u_pass:
                    st.session_state.update({"logged_in": True, "user_name": match.iloc[0]['Name'], "role": match.iloc[0]['Role']})
                    st.rerun()
                else: st.error("Invalid Credentials")
else:
    # --- LOAD FULL DATABASES ---
    user_df = load_data(USER_DB, ["Name", "Email", "Password", "Role", "Manager"])
    task_df = load_data(TASK_DB, ["Date", "Client", "Tower", "Activity", "SOP_Link", "Owner", "Reviewer", "Frequency", "WD_Marker", "Start_Time", "End_Time", "Status", "Comments"])
    client_df = load_data(CLIENT_DB, ["Client_Name"])

    # --- SIDEBAR ---
    st.sidebar.title("BGA F&A")
    st.sidebar.info(f"Connected: {st.session_state['user_name']}\n\nToday: {get_current_wd()}")
    
    menu = ["📊 Dashboard", "➕ Assign Activity", "🏢 Clients", "👥 Manage Team", "📅 WD Calendar"]
    choice = st.sidebar.radio("Navigation", menu)
    
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()

    # --- 1. DASHBOARD ---
    if choice == "📊 Dashboard":
        st.header("Operations Dashboard")
        
        # Filtering
        if st.session_state['role'] == "Admin":
            display_df = task_df
        elif st.session_state['role'] == "Manager":
            display_df = task_df[(task_df['Owner'] == st.session_state['user_name']) | (task_df['Reviewer'] == st.session_state['user_name'])]
        else:
            display_df = task_df[task_df['Owner'] == st.session_state['user_name']]

        edited_df = st.data_editor(
            display_df, 
            column_config={
                "SOP_Link": st.column_config.LinkColumn("🔗 SOP"),
                "Status": st.column_config.SelectboxColumn("Status", options=["🔴 Pending", "🟡 In Progress", "🔍 QC Required", "✅ Approved"]),
                "Start_Time": st.column_config.TimeColumn("Start"),
                "End_Time": st.column_config.TimeColumn("End"),
                "Frequency": st.column_config.SelectboxColumn("Frequency", options=["Daily", "Weekly", "Monthly", "Ad-hoc"])
            },
            use_container_width=True, 
            key="main_editor"
        )
        
        if st.button("Save Changes"):
            task_df.update(edited_df)
            save_data(task_df, TASK_DB)
            st.success("Database Updated Successfully!")

    # --- 2. ASSIGN ACTIVITY ---
    elif choice == "➕ Assign Activity":
        st.header("Assign New Task")
        with st.form("task_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            f_client = col1.selectbox("Client", client_df['Client_Name'].tolist() if not client_df.empty else ["No Clients Registered"])
            f_tower = col2.selectbox("Tower", ["O2C", "P2P", "R2R"])
            f_act = st.text_input("Task Description")
            f_sop = st.text_input("SOP URL Link")
            f_wd = col1.text_input("WD Marker (e.g. WD 1)")
            f_freq = col2.selectbox("Frequency", ["Daily", "Weekly", "Monthly", "Ad-hoc"])
            f_owner = col1.selectbox("Action Owner", user_df['Name'].tolist())
            f_reviewer = col2.selectbox("Reviewer", user_df[user_df['Role'].isin(['Manager', 'Admin'])]['Name'].tolist())
            
            if st.form_submit_button("Publish Task"):
                new_task = pd.DataFrame([{
                    "Date": date.today().strftime("%Y-%m-%d"), "Client": f_client, "Tower": f_tower, 
                    "Activity": f_act, "SOP_Link": f_sop, "Owner": f_owner, "Reviewer": f_reviewer,
                    "Frequency": f_freq, "WD_Marker": f_wd, "Status": "🔴 Pending"
                }])
                task_df = pd.concat([task_df, new_task], ignore_index=True)
                save_data(task_df, TASK_DB)
                st.success("Task assigned successfully!")

    # --- 3. CLIENTS ---
    elif choice == "🏢 Clients":
        st.header("Client Master")
        with st.form("client_form", clear_on_submit=True):
            new_client = st.text_input("Client Name")
            if st.form_submit_button("Add Client"):
                if new_client:
                    client_df = pd.concat([client_df, pd.DataFrame([{"Client_Name": new_client}])], ignore_index=True)
                    save_data(client_df, CLIENT_DB)
                    st.rerun()

    # --- 4. MANAGE TEAM ---
    elif choice == "👥 Manage Team":
        st.header("Team Management")
        with st.form("user_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            n = col1.text_input("Name")
            e = col2.text_input("Email")
            r = col1.selectbox("Role", ["User", "Manager", "Admin"])
            m = col2.selectbox("Reporting Manager", ["None"] + user_df[user_df['Role'].isin(['Manager', 'Admin'])]['Name'].tolist())
            if st.form_submit_button("Add Member"):
                new_u = pd.DataFrame([{"Name": n, "Email": e, "Role": r, "Manager": m, "Password": "welcome123"}])
                user_df = pd.concat([user_df, new_u], ignore_index=True)
                save_data(user_df, USER_DB)
                st.rerun()
        st.dataframe(user_df[["Name", "Email", "Role", "Manager"]], use_container_width=True)

    # --- 5. CALENDAR ---
    elif choice == "📅 WD Calendar":
        st.header("Calendar Setup")
        if st.button("Regenerate Dates for Current Month"):
            import calendar
            today = date.today()
            dates = [date(today.year, today.month, d).strftime("%Y-%m-%d") for d in range(1, calendar.monthrange(today.year, today.month)[1] + 1)]
            new_cal = pd.DataFrame({"Date": dates, "Is_Holiday": [False]*len(dates)})
            save_data(new_cal, CALENDAR_DB)
            st.rerun()
        
        cal_e = st.data_editor(load_data(CALENDAR_DB, ["Date", "Is_Holiday"]), use_container_width=True)
        if st.button("Update Calendar"):
            save_data(cal_e, CALENDAR_DB)
