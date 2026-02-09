import streamlit as st
import pandas as pd
import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, date
import base64

# --- 1. CONFIG & UI CLEANUP ---
st.set_page_config(page_title="BGA F&A Workflow", layout="wide")

# CSS to hide the Streamlit Header, Toolbar, and Footer
hide_style = """
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
    [data-testid="stToolbar"] {visibility: hidden !important;}
    </style>
"""
st.markdown(hide_style, unsafe_allow_html=True)

# --- 2. DATABASE FILES ---
USER_DB = "users.csv"
TASK_DB = "database.csv"
CALENDAR_DB = "calendar.csv"
CLIENT_DB = "clients.csv"

def load_data(file, columns):
    if not os.path.exists(file): return pd.DataFrame(columns=columns)
    try:
        df = pd.read_csv(file)
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
    month_days = cal_df[cal_df['Date'].str.startswith(date.today().strftime("%Y-%m"))]
    working_days = month_days[month_days['Is_Holiday'] == False].sort_values('Date')
    
    wd_count = 0
    for idx, row in working_days.iterrows():
        wd_count += 1
        if row['Date'] == today_str: return f"WD {wd_count}"
    return "Holiday/Weekend"

# --- 4. SESSION STATE ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

# --- 5. LOGIN ---
if not st.session_state['logged_in']:
    st.header("🔑 BGA F&A Portal Login")
    user_df = load_data(USER_DB, ["Name", "Email", "Password", "Role", "Manager"])
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
    logo_path = "1 BGA Logo Colour.png"
    if os.path.exists(logo_path): st.sidebar.image(logo_path, use_container_width=True)
    
    current_wd = get_current_wd()
    st.sidebar.metric("Today's Schedule", current_wd)
    
    menu = ["📊 Dashboard", "👤 My Profile"]
    if st.session_state['role'] in ["Admin", "Manager"]: 
        menu.extend(["➕ Assign Activity", "🏢 Clients"])
    if st.session_state['role'] == "Admin": 
        menu.extend(["👥 Manage Team", "📅 WD Calendar"])
    
    choice = st.sidebar.radio("Navigation", menu)
    st.sidebar.divider()
    st.sidebar.write(f"**Logged in as:** {st.session_state['user_name']}")

    if choice == "📊 Dashboard":
        st.subheader(f"Schedule for {date.today().strftime('%d %B %Y')}")
        
        # Filtering
        if st.session_state['role'] == "Admin":
            view_df = task_df
        elif st.session_state['role'] == "Manager":
            view_df = task_df[(task_df['Owner'] == st.session_state['user_name']) | (task_df['Reviewer'] == st.session_state['user_name'])]
        else:
            view_df = task_df[task_df['Owner'] == st.session_state['user_name']]

        is_user = st.session_state['role'] == "User"
        
        # Professional Grid View
        updated_df = st.data_editor(
            view_df,
            column_config={
                "SOP_Link": st.column_config.LinkColumn("🔗 SOP"),
                "Status": st.column_config.SelectboxColumn("Status", options=["🔴 Pending", "🟡 In Progress", "🔍 QC Required", "✅ Approved"]),
                "Start_Time": st.column_config.TimeColumn("Start Time"),
                "End_Time": st.column_config.TimeColumn("End Time"),
                "Reviewer": st.column_config.SelectboxColumn("Reviewer", options=user_df[user_df['Role'].isin(['Admin', 'Manager'])]['Name'].tolist(), disabled=is_user),
                "Client": st.column_config.TextColumn(disabled=is_user),
                "Tower": st.column_config.TextColumn(disabled=is_user),
                "Activity": st.column_config.TextColumn(disabled=is_user),
            },
            use_container_width=True,
            num_rows="fixed",
            key="fa_editor"
        )
        
        col_s1, col_s2 = st.columns([1, 5])
        if col_s1.button("💾 Save Progress"):
            task_df.update(updated_df)
            save_data(task_df, TASK_DB)
            st.toast("Sync Complete!", icon="✅")
        col_s2.caption(f"Last Synced: {datetime.now().strftime('%H:%M:%S')}")

    elif choice == "🏢 Clients":
        st.header("Client Master")
        new_c = st.text_input("New Client Name")
        if st.button("Add Client"):
            save_data(pd.concat([client_df, pd.DataFrame([{"Client_Name": new_c}])], ignore_index=True), CLIENT_DB)
            st.rerun()
        st.dataframe(client_df, use_container_width=True)

    elif choice == "➕ Assign Activity":
        st.header("📝 Assignment")
        with st.form("fa_task"):
            c1, c2, c3 = st.columns(3)
            client = c1.selectbox("Client", client_df['Client_Name'].tolist() if not client_df.empty else ["Add Clients First"])
            tower = c2.selectbox("Tower", ["O2C", "P2P", "R2R"])
            act = c3.text_input("Activity")
            
            sop = c1.text_input("SOP URL")
            freq = c2.selectbox("Frequency", ["Daily", "Weekly", "Monthly", "Ad-hoc"])
            wd = c3.text_input("WD Marker")
            
            owner = c1.selectbox("Action Owner", user_df['Name'].tolist())
            reviewer = c2.selectbox("Reporting Manager", user_df[user_df['Role'].isin(['Admin', 'Manager'])]['Name'].tolist())
            
            if st.form_submit_button("Assign Task"):
                new_t = pd.DataFrame([{"Date": date.today().strftime("%Y-%m-%d"), "Client": client, "Tower": tower, "Activity": act, 
                                       "SOP_Link": sop, "Owner": owner, "Reviewer": reviewer, "Frequency": freq, "WD_Marker": wd, "Status": "🔴 Pending"}])
                save_data(pd.concat([task_df, new_t], ignore_index=True), TASK_DB)
                st.success("Task Assigned")

    elif choice == "📅 WD Calendar":
        st.header("Calendar Setup")
        if st.button("Gen Month"):
            import calendar
            y, m = date.today().year, date.today().month
            dates = [date(y, m, d).strftime("%Y-%m-%d") for d in range(1, calendar.monthrange(y, m)[1] + 1)]
            save_data(pd.DataFrame({"Date": dates, "Is_Holiday": [False]*len(dates)}), CALENDAR_DB)
            st.rerun()
        cal_e = st.data_editor(load_data(CALENDAR_DB, ["Date", "Is_Holiday"]), use_container_width=True)
        if st.button("Save Calendar"): save_data(cal_e, CALENDAR_DB)

    elif choice == "👥 Manage Team":
        st.header("Team Management")
        st.dataframe(user_df[["Name", "Email", "Role", "Manager"]], use_container_width=True)
        with st.form("u_add"):
            n, e, r = st.text_input("Name"), st.text_input("Email"), st.selectbox("Role", ["User", "Manager", "Admin"])
            m = st.selectbox("Reporting Manager", user_df[user_df['Role'].isin(['Admin', 'Manager'])]['Name'].tolist())
            if st.form_submit_button("Add Member"):
                save_data(pd.concat([user_df, pd.DataFrame([{"Name":n,"Email":e,"Password":"welcome123","Role":r,"Manager":m}])], ignore_index=True), USER_DB)
                st.rerun()

    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()
