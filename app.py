import streamlit as st
import pandas as pd
import os
from datetime import datetime, date

# --- 1. CONFIG & LIGHT ASH UI STYLING ---
st.set_page_config(page_title="BGA F&A Workflow", layout="wide")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="stToolbar"] {visibility: hidden !important;}
    
    /* MAIN CONTENT AREA - VERY LIGHT ASH */
    .stApp { 
        background-color: #f2f2f2 !important; /* Very Light Ash */
        color: #000000 !important;
    }
    
    /* Force all text in main area to Black */
    .stApp h1, .stApp h2, .stApp h3, .stApp p, .stApp label, .stApp span {
        color: #000000 !important;
    }
    
    /* SIDEBAR - CLEAN WHITE */
    section[data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 1px solid #d1d1d1;
    }
    
    /* Sidebar Text Fix */
    section[data-testid="stSidebar"] .stText, 
    section[data-testid="stSidebar"] label, 
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] span {
        color: #000000 !important;
    }

    div[data-testid="stSidebarNav"] ul li div span {
        color: #000000 !important;
        font-weight: 600 !important;
    }

    /* DATA EDITOR CONTAINER */
    div[data-testid="stVerticalBlock"] > div:has(div.stDataFrame) {
        background-color: #ffffff; /* Contrast white cards on ash background */
        padding: 15px;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
    }

    /* LOGOUT BUTTON */
    div.stButton > button:contains("Logout") {
        background-color: #f8f9fa !important;
        color: #000000 !important;
        border: 1px solid #cccccc !important;
        font-weight: bold !important;
        width: 100% !important;
    }
    
    /* Green Sync Notification (Toast) Override */
    [data-testid="stToast"] {
        background-color: #28a745 !important;
        color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA UTILITIES ---
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
                    st.session_state.update({"logged_in": True, "user_name": "Master Admin", "role": "Admin", "user_email": u_email})
                    st.rerun()
                elif not user_df.empty:
                    match = user_df[user_df['Email'].str.lower() == u_email]
                    if not match.empty and str(match.iloc[0]['Password']) == u_pass:
                        st.session_state.update({"logged_in": True, "user_name": match.iloc[0]['Name'], "role": match.iloc[0]['Role'], "user_email": u_email})
                        st.rerun()
                    else: st.error("Invalid Credentials")
else:
    # --- MAIN APP ---
    user_df = load_data(USER_DB, ["Name", "Email", "Password", "Role", "Manager"])
    task_df = load_data(TASK_DB, ["Date", "Client", "Tower", "Activity", "SOP_Link", "Owner", "Reviewer", "Frequency", "WD_Marker", "Start_Time", "End_Time", "Status", "Comments"])
    client_df = load_data(CLIENT_DB, ["Client_Name"])

    # Sidebar
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

    # --- DASHBOARD WITH AUTO-SAVE ---
    if choice == "📊 Dashboard":
        st.title(f"Operations Dashboard")
        
        # Filtering logic
        if st.session_state['role'] == "Admin": view_df = task_df
        elif st.session_state['role'] == "Manager":
            view_df = task_df[(task_df['Owner'] == st.session_state['user_name']) | (task_df['Reviewer'] == st.session_state['user_name'])]
        else: view_df = task_df[task_df['Owner'] == st.session_state['user_name']]

        # Data Editor
        edited_df = st.data_editor(
            view_df,
            column_config={
                "SOP_Link": st.column_config.LinkColumn("🔗 SOP"),
                "Status": st.column_config.SelectboxColumn("Status", options=["🔴 Pending", "🟡 In Progress", "🔍 QC Required", "✅ Approved"]),
                "Start_Time": st.column_config.TimeColumn("Start"),
                "End_Time": st.column_config.TimeColumn("End"),
            },
            use_container_width=True,
            key="fa_editor"
        )
        
        # AUTO-SAVE LOGIC
        if st.session_state.get("fa_editor") and st.session_state.fa_editor["edited_rows"]:
            task_df.update(edited_df)
            save_data(task_df, TASK_DB)
            st.toast("Changes saved automatically", icon="☁️")

    # (Include other menu logic for Assign Activity, Clients, Team, Calendar same as previous version)
