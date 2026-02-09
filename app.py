import streamlit as st
import pandas as pd
import os
from datetime import datetime, date

# --- 1. CONFIG (Default Streamlit Theme) ---
st.set_page_config(page_title="BGA F&A Workflow", layout="wide")

# --- 2. DATA UTILITIES ---
USER_DB, TASK_DB, CALENDAR_DB, CLIENT_DB = "users.csv", "database.csv", "calendar.csv", "clients.csv"

def load_data(file, columns):
    if not os.path.exists(file): 
        return pd.DataFrame(columns=columns)
    try:
        df = pd.read_csv(file)
        # Ensure all required columns exist
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
    # Convert 'Is_Holiday' to boolean if it's string-based
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
            
            # Master Admin Bypass
            if u_email == "admin@thebga.io" and u_pass == "admin123":
                st.session_state.update({"logged_in": True, "user_name": "Admin", "role": "Admin"})
                st.rerun()
            elif not user_df.empty:
                match = user_df[user_df['Email'].str.lower() == u_email]
                if not match.empty and str(match.iloc[0]['Password']) == u_pass:
                    st.session_state.update({
                        "logged_in": True, 
                        "user_name": match.iloc[0]['Name'], 
                        "role": match.iloc[0]['Role']
                    })
                    st.rerun()
                else: st.error("Invalid Credentials")
            else: st.error("User database not found. Use Master Admin.")
else:
    # --- LOAD DATABASES ---
    user_df = load_data(USER_DB, ["Name", "Email", "Password", "Role", "Manager"])
    task_df = load_data(TASK_DB, ["Date", "Client", "Tower", "Activity", "Owner", "Reviewer", "Status", "Start_Time", "End_Time"])
    client_df = load_data(CLIENT_DB, ["Client_Name"])

    # --- SIDEBAR NAVIGATION ---
    st.sidebar.title("BGA Navigation")
    st.sidebar.write(f"Logged in as: **{st.session_state['user_name']}**")
    st.sidebar.info(f"Today: {get_current_wd()}")
    
    menu = ["📊 Dashboard", "➕ Assign Activity", "🏢 Clients", "👥 Manage Team", "📅 WD Calendar"]
    choice = st.sidebar.radio("Go to:", menu)
    
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()

    # --- 1. DASHBOARD ---
    if choice == "📊 Dashboard":
        st.header("Operations Dashboard")
        
        # Simple Role Filter
        if st.session_state['role'] == "Admin":
            display_df = task_df
        else:
            display_df = task_df[task_df['Owner'] == st.session_state['user_name']]

        edited_df = st.data_editor(display_df, use_container_width=True, key="main_editor")
        
        if st.button("Save Dashboard Changes"):
            # Update master task_df with changes from display_df
            task_df.update(edited_df)
            save_data(task_df, TASK_DB)
            st.success("Changes Saved to Database!")

    # --- 2. ASSIGN ACTIVITY ---
    elif choice == "➕ Assign Activity":
        st.header("Create New Task")
        with st.form("task_form", clear_on_submit=True):
            c_list = client_df['Client_Name'].tolist() if not client_df.empty else ["Default"]
            u_list = user_df['Name'].tolist() if not user_df.empty else ["Admin"]
            
            f_client = st.selectbox("Client", c_list)
            f_tower = st.selectbox("Tower", ["O2C", "P2P", "R2R"])
            f_act = st.text_input("Activity Description")
            f_owner = st.selectbox("Owner", u_list)
            
            if st.form_submit_button("Assign Task"):
                new_task = pd.DataFrame([{
                    "Date": date.today().strftime("%Y-%m-%d"),
                    "Client": f_client, "Tower": f_tower, "Activity": f_act,
                    "Owner": f_owner, "Status": "Pending"
                }])
                task_df = pd.concat([task_df, new_task], ignore_index=True)
                save_data(task_df, TASK_DB)
                st.success("Task added!")

    # --- 3. CLIENTS ---
    elif choice == "🏢 Clients":
        st.header("Client Master")
        with st.form("client_form", clear_on_submit=True):
            new_client_name = st.text_input("Enter New Client Name")
            if st.form_submit_button("Register Client"):
                if new_client_name:
                    new_c = pd.DataFrame([{"Client_Name": new_client_name}])
                    client_df = pd.concat([client_df, new_c], ignore_index=True)
                    save_data(client_df, CLIENT_DB)
                    st.success("Client registered!")
                    st.rerun()
        st.dataframe(client_df, use_container_width=True)

    # --- 4. MANAGE TEAM ---
    elif choice == "👥 Manage Team":
        st.header("Team Management")
        with st.form("user_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            n = col1.text_input("Name")
            e = col2.text_input("Email")
            r = col1.selectbox("Role", ["User", "Manager", "Admin"])
            p = col2.text_input("Password", value="welcome123")
            
            if st.form_submit_button("Add Member"):
                new_u = pd.DataFrame([{"Name": n, "Email": e, "Role": r, "Password": p}])
                user_df = pd.concat([user_df, new_u], ignore_index=True)
                save_data(user_df, USER_DB)
                st.success("User added!")
                st.rerun()
        st.dataframe(user_df[["Name", "Email", "Role"]], use_container_width=True)

    # --- 5. CALENDAR ---
    elif choice == "📅 WD Calendar":
        st.header("Calendar Setup")
        st.write("Set 'Is_Holiday' to True for weekends/holidays.")
        
        # Quick-gen month button
        if st.button("Generate Current Month Dates"):
            import calendar
            today = date.today()
            num_days = calendar.monthrange(today.year, today.month)[1]
            dates = [date(today.year, today.month, d).strftime("%Y-%m-%d") for d in range(1, num_days + 1)]
            new_cal = pd.DataFrame({"Date": dates, "Is_Holiday": [False]*len(dates)})
            save_data(new_cal, CALENDAR_DB)
            st.rerun()

        current_cal = load_data(CALENDAR_DB, ["Date", "Is_Holiday"])
        edited_cal = st.data_editor(current_cal, use_container_width=True)
        if st.button("Save Calendar Changes"):
            save_data(edited_cal, CALENDAR_DB)
            st.success("Calendar updated!")
