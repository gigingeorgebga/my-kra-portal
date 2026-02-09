import streamlit as st
import pandas as pd
import os
from datetime import datetime, date

# --- 1. CONFIG & INVERTED UI STYLING ---
st.set_page_config(page_title="BGA F&A Workflow", layout="wide")

st.markdown("""
    <style>
    /* 1. HIDE DEFAULT ELEMENTS */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="stToolbar"] {visibility: hidden !important;}
    
    /* 2. MAIN CONTENT AREA (RIGHT SIDE) - Dark BGA Navy */
    .stApp { 
        background-color: #1e1e3f !important; 
        color: #ffffff !important;
    }
    
    /* Force all text in main area to White */
    .stApp h1, .stApp h2, .stApp h3, .stApp p, .stApp label, .stApp span {
        color: #ffffff !important;
    }
    
    /* 3. SIDEBAR (LEFT SIDE) - Clean White */
    section[data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 1px solid #e0e0e0;
    }
    
    /* Force Sidebar Text to Black */
    section[data-testid="stSidebar"] .stText, 
    section[data-testid="stSidebar"] label, 
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] span {
        color: #000000 !important;
    }

    /* Sidebar Navigation Radio Buttons */
    div[data-testid="stSidebarNav"] ul li div span {
        color: #000000 !important;
        font-weight: 600 !important;
    }
    
    /* 4. DATA EDITOR / TABLES (Keep readable) */
    /* We keep the spreadsheet area slightly light for visibility against dark bg */
    [data-testid="stMetricValue"] {
        color: #ffffff !important;
    }
    
    div[data-testid="stVerticalBlock"] > div:has(div.stDataFrame) {
        background-color: #2d2d5a; /* Slightly lighter navy for contrast */
        padding: 15px;
        border-radius: 10px;
    }

    /* 5. BUTTONS */
    /* Sync Button - Professional Green */
    div.stButton > button:first-child:contains("Sync") {
        background-color: #28a745 !important;
        color: white !important;
        border: none !important;
    }

    /* Logout Button - Black font on Gray/White background */
    div.stButton > button:contains("Logout") {
        background-color: #f0f2f6 !important;
        color: #000000 !important;
        border: 1px solid #d1d1e0 !important;
        font-weight: bold !important;
        width: 100% !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATABASE FILES ---
USER_DB, TASK_DB, CALENDAR_DB, CLIENT_DB = "users.csv", "database.csv", "calendar.csv", "clients.csv"

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
    return "Non-Working Day"

# --- 4. SESSION STATE & LOGIN ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    col_l, col_r = st.columns([1, 1])
    with col_l:
        st.image("1 BGA Logo Colour.png", width=200)
        st.title("BGA F&A Portal")
    with col_r:
        with st.container(border=True):
            u_email = st.text_input("Email").strip().lower()
            u_pass = st.text_input("Password", type="password").strip()
            if st.button("Sign In", use_container_width=True):
                user_df = load_data(USER_DB, ["Name", "Email", "Password", "Role", "Manager"])
                if u_email == "admin@thebga.io" and u_pass == "admin123":
                    st.session_state.update({"logged_in": True, "user_name": "Master Admin", "role": "Admin", "user_email": u_email, "must_change": False})
                    st.rerun()
                elif not user_df.empty:
                    match = user_df[user_df['Email'].str.lower() == u_email]
                    if not match.empty and str(match.iloc[0]['Password']) == u_pass:
                        st.session_state.update({"logged_in": True, "user_name": match.iloc[0]['Name'], "role": match.iloc[0]['Role'], "user_email": u_email, "must_change": (u_pass == "welcome123")})
                        st.rerun()
                    else: st.error("Incorrect details")
else:
    # --- MAIN APP ---
    user_df = load_data(USER_DB, ["Name", "Email", "Password", "Role", "Manager", "Photo"])
    task_df = load_data(TASK_DB, ["Date", "Client", "Tower", "Activity", "SOP_Link", "Owner", "Reviewer", "Frequency", "WD_Marker", "Start_Time", "End_Time", "Status", "Comments"])
    client_df = load_data(CLIENT_DB, ["Client_Name"])

    # Sidebar (White background, Black text)
    logo_path = "1 BGA Logo Colour.png"
    if os.path.exists(logo_path): st.sidebar.image(logo_path, use_container_width=True)
    
    st.sidebar.markdown(f"**Calendar Context:**")
    st.sidebar.info(get_current_wd())
    st.sidebar.divider()
    
    menu = ["📊 Dashboard", "👤 My Profile"]
    if st.session_state['role'] in ["Admin", "Manager"]: menu.extend(["➕ Assign Activity", "🏢 Clients"])
    if st.session_state['role'] == "Admin": menu.extend(["👥 Manage Team", "📅 WD Calendar"])
    
    choice = st.sidebar.radio("Navigation", menu)
    st.sidebar.divider()
    st.sidebar.write(f"Connected: **{st.session_state['user_name']}**")

    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()

    # DASHBOARD (Dark area, White text)
    if choice == "📊 Dashboard":
        st.title(f"Operations Dashboard")
        
        if st.session_state['role'] == "Admin": view_df = task_df
        elif st.session_state['role'] == "Manager":
            view_df = task_df[(task_df['Owner'] == st.session_state['user_name']) | (task_df['Reviewer'] == st.session_state['user_name'])]
        else: view_df = task_df[task_df['Owner'] == st.session_state['user_name']]

        updated_df = st.data_editor(
            view_df,
            column_config={
                "SOP_Link": st.column_config.LinkColumn("🔗 SOP"),
                "Status": st.column_config.SelectboxColumn("Status", options=["🔴 Pending", "🟡 In Progress", "🔍 QC Required", "✅ Approved"]),
            },
            use_container_width=True,
            key="fa_dashboard"
        )
        
        if st.button("💾 Sync to Database"):
            task_df.update(updated_df)
            save_data(task_df, TASK_DB)
            st.toast("Sync Success!", icon="🚀")

    # (Other pages follow same structure)
    elif choice == "➕ Assign Activity":
        st.title("Assign Activity")
        with st.form("task_creation"):
            client = st.selectbox("Client", client_df['Client_Name'].tolist() if not client_df.empty else ["No Clients"])
            tower = st.selectbox("Tower", ["O2C", "P2P", "R2R"])
            act = st.text_input("Task Description")
            freq = st.selectbox("Frequency", ["Daily", "Weekly", "Monthly", "Ad-hoc"])
            wd = st.text_input("WD Marker")
            owner = st.selectbox("Action Owner", user_df['Name'].tolist())
            if st.form_submit_button("Confirm Assignment"):
                new_t = pd.DataFrame([{"Date": date.today().strftime("%Y-%m-%d"), "Client": client, "Tower": tower, "Activity": act, "Owner": owner, "Frequency": freq, "WD_Marker": wd, "Status": "🔴 Pending"}])
                save_data(pd.concat([task_df, new_t], ignore_index=True), TASK_DB)
                st.success("Task Published")

    elif choice == "🏢 Clients":
        st.title("Client Master")
        new_c = st.text_input("Add Client")
        if st.button("Add"): 
            save_data(pd.concat([client_df, pd.DataFrame([{"Client_Name": new_c}])], ignore_index=True), CLIENT_DB)
            st.rerun()
        st.dataframe(client_df, use_container_width=True)

    elif choice == "👥 Manage Team":
        st.title("Team Management")
        st.dataframe(user_df[["Name", "Email", "Role", "Manager"]], use_container_width=True)
        with st.expander("Register User"):
            n, e = st.text_input("Name"), st.text_input("Email")
            r = st.selectbox("Role", ["User", "Manager", "Admin"])
            m = st.selectbox("Manager", user_df[user_df['Role'].isin(['Admin', 'Manager'])]['Name'].tolist())
            if st.button("Add"):
                save_data(pd.concat([user_df, pd.DataFrame([{"Name":n,"Email":e,"Password":"welcome123","Role":r,"Manager":m}])], ignore_index=True), USER_DB)
                st.rerun()

    elif choice == "📅 WD Calendar":
        st.title("Work Day Setup")
        if st.button("Gen Month"):
            import calendar
            y, m = date.today().year, date.today().month
            dates = [date(y, m, d).strftime("%Y-%m-%d") for d in range(1, calendar.monthrange(y, m)[1] + 1)]
            save_data(pd.DataFrame({"Date": dates, "Is_Holiday": [False]*len(dates)}), CALENDAR_DB)
            st.rerun()
        cal_e = st.data_editor(load_data(CALENDAR_DB, ["Date", "Is_Holiday"]), use_container_width=True)
        if st.button("Save"): save_data(cal_e, CALENDAR_DB)
