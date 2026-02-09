import streamlit as st
import pandas as pd
import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, date
import base64

# --- 1. CONFIG & HIGH-CONTRAST UI STYLING ---
st.set_page_config(page_title="BGA F&A Workflow", layout="wide")

st.markdown("""
    <style>
    /* Hide default Streamlit elements */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="stToolbar"] {visibility: hidden !important;}
    
    /* Overall Background */
    .stApp { background-color: #f8f9fa; }
    
    /* SIDEBAR BRIGHTNESS FIX */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0e1117 0%, #1c1f26 100%) !important;
    }
    
    /* Force Sidebar Text to White */
    section[data-testid="stSidebar"] .stText, 
    section[data-testid="stSidebar"] label, 
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] .st-at {
        color: #ffffff !important;
        font-weight: 500 !important;
    }

    /* Make Radio Button Labels White */
    div[data-testid="stSidebarNav"] ul li div span {
        color: white !important;
    }
    
    /* Make the BGA Logo White */
    [data-testid="stSidebar"] img {
        filter: brightness(0) invert(1);
        padding-bottom: 20px;
    }

    /* Card-like containers for data */
    div[data-testid="stVerticalBlock"] > div:has(div.stDataFrame) {
        background-color: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    }
    
    /* Button Styling */
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    /* Green Sync Button */
    div.stButton > button:first-child:contains("Sync") {
        background-color: #28a745 !important;
        color: white !important;
        border: none;
    }

    /* Logout Button Styling */
    div.stButton > button:contains("Logout") {
        background-color: #dc3545 !important;
        color: white !important;
        border: none;
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
        st.caption("Operations & Productivity Tracking")
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
    # --- MAIN APP (LOGGED IN) ---
    user_df = load_data(USER_DB, ["Name", "Email", "Password", "Role", "Manager", "Photo"])
    task_df = load_data(TASK_DB, ["Date", "Client", "Tower", "Activity", "SOP_Link", "Owner", "Reviewer", "Frequency", "WD_Marker", "Start_Time", "End_Time", "Status", "Comments"])
    client_df = load_data(CLIENT_DB, ["Client_Name"])

    # Sidebar 
    logo_path = "1 BGA Logo Colour.png"
    if os.path.exists(logo_path): st.sidebar.image(logo_path, use_container_width=True)
    
    st.sidebar.subheader(f"📅 {get_current_wd()}")
    st.sidebar.divider()
    
    menu = ["📊 Dashboard", "👤 My Profile"]
    if st.session_state['role'] in ["Admin", "Manager"]: menu.extend(["➕ Assign Activity", "🏢 Clients"])
    if st.session_state['role'] == "Admin": menu.extend(["👥 Manage Team", "📅 WD Calendar"])
    
    choice = st.sidebar.radio("Navigation", menu)
    st.sidebar.divider()
    st.sidebar.write(f"Connected: **{st.session_state['user_name']}**")

    # DASHBOARD
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
                "Reviewer": st.column_config.SelectboxColumn("Reviewer", options=user_df[user_df['Role'].isin(['Admin', 'Manager'])]['Name'].tolist()),
                "Start_Time": st.column_config.TimeColumn("Start"),
                "End_Time": st.column_config.TimeColumn("End"),
            },
            use_container_width=True,
            key="fa_dashboard"
        )
        
        c1, c2 = st.columns([1, 4])
        if c1.button("💾 Sync to Database", use_container_width=True):
            task_df.update(updated_df)
            save_data(task_df, TASK_DB)
            st.toast("Sync Success!", icon="🚀")
        c2.caption(f"Last Synced: {datetime.now().strftime('%H:%M:%S')}")

    # (Other pages like Assign Activity, Clients, etc. follow the same logic as previous version)
    elif choice == "➕ Assign Activity":
        st.title("Assign New Task")
        with st.container(border=True):
            with st.form("task_creation"):
                c1, c2 = st.columns(2)
                client = c1.selectbox("Client", client_df['Client_Name'].tolist() if not client_df.empty else ["No Clients Found"])
                tower = c2.selectbox("Process Tower", ["O2C", "P2P", "R2R"])
                act = st.text_input("Task Description")
                
                c3, c4, c5 = st.columns(3)
                freq = c3.selectbox("Frequency", ["Daily", "Weekly", "Monthly", "Ad-hoc"])
                wd = c4.text_input("Work Day (WD Marker)")
                sop = c5.text_input("SOP Link")
                
                c6, c7 = st.columns(2)
                owner = c6.selectbox("Action Owner", user_df['Name'].tolist())
                reviewer = c7.selectbox("Reporting Manager", user_df[user_df['Role'].isin(['Admin', 'Manager'])]['Name'].tolist())
                
                if st.form_submit_button("Confirm Assignment", use_container_width=True):
                    new_t = pd.DataFrame([{"Date": date.today().strftime("%Y-%m-%d"), "Client": client, "Tower": tower, "Activity": act, 
                                           "SOP_Link": sop, "Owner": owner, "Reviewer": reviewer, "Frequency": freq, "WD_Marker": wd, "Status": "🔴 Pending"}])
                    save_data(pd.concat([task_df, new_t], ignore_index=True), TASK_DB)
                    st.success("Task Published")

    elif choice == "🏢 Clients":
        st.title("Client Master")
        new_c = st.text_input("Add Client")
        if st.button("Add"): 
            save_data(pd.concat([client_df, pd.DataFrame([{"Client_Name": new_c}])], ignore_index=True), CLIENT_DB)
            st.rerun()
        st.dataframe(client_df, use_container_width=True)

    elif choice == "📅 WD Calendar":
        st.title("Work Day Calendar")
        if st.button("Auto-Generate Current Month"):
            import calendar
            y, m = date.today().year, date.today().month
            dates = [date(y, m, d).strftime("%Y-%m-%d") for d in range(1, calendar.monthrange(y, m)[1] + 1)]
            save_data(pd.DataFrame({"Date": dates, "Is_Holiday": [False]*len(dates)}), CALENDAR_DB)
            st.rerun()
        cal_data = st.data_editor(load_data(CALENDAR_DB, ["Date", "Is_Holiday"]), use_container_width=True)
        if st.button("Save Changes"): save_data(cal_data, CALENDAR_DB)

    elif choice == "👥 Manage Team":
        st.title("Team Management")
        st.dataframe(user_df[["Name", "Email", "Role", "Manager"]], use_container_width=True)
        with st.expander("Add New Team Member"):
            n, e, r = st.text_input("Full Name"), st.text_input("Email"), st.selectbox("Access Level", ["User", "Manager", "Admin"])
            m = st.selectbox("Manager", user_df[user_df['Role'].isin(['Admin', 'Manager'])]['Name'].tolist())
            if st.button("Register"):
                save_data(pd.concat([user_df, pd.DataFrame([{"Name":n,"Email":e,"Password":"welcome123","Role":r,"Manager":m}])], ignore_index=True), USER_DB)
                st.rerun()

    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.clear()
        st.rerun()
