import streamlit as st
import pandas as pd
import os
from datetime import datetime, date

# --- 1. CONFIG & HIGH-VISIBILITY STYLING ---
st.set_page_config(page_title="BGA F&A Workflow", layout="wide")

st.markdown("""
    <style>
    /* 1. HIDE DEFAULT ELEMENTS */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="stToolbar"] {visibility: hidden !important;}
    
    /* 2. MAIN CONTENT AREA - VERY LIGHT ASH */
    .stApp { 
        background-color: #f2f2f2 !important; 
    }

    /* 3. GLOBAL FONT FORCE - BLACK EVERYTHING ON RIGHT SIDE */
    /* This targets headers, paragraphs, labels, and even data editor cells */
    .stApp h1, .stApp h2, .stApp h3, .stApp p, .stApp label, .stApp span, .stApp div, .stApp input {
        color: #000000 !important;
    }

    /* 4. SIDEBAR - CLEAN WHITE */
    section[data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 1px solid #d1d1e0;
    }
    
    /* Ensure Sidebar text is also black */
    section[data-testid="stSidebar"] * {
        color: #000000 !important;
    }

    /* 5. DATA EDITOR SPECIFIC FIX */
    /* Ensures the text inside the spreadsheet cells is visible */
    [data-testid="stTable"] td, [data-testid="stDataFrame"] div {
        color: #000000 !important;
    }
    
    /* Card Container for tables */
    div[data-testid="stVerticalBlock"] > div:has(div.stDataFrame) {
        background-color: #ffffff !important;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #cccccc;
    }

    /* LOGOUT BUTTON - BLACK TEXT */
    div.stButton > button:contains("Logout") {
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 1px solid #000000 !important;
        font-weight: bold !important;
        width: 100% !important;
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
    # --- MAIN APP (LOGGED IN) ---
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

    # --- PAGES ---
    if choice == "📊 Dashboard":
        st.title(f"Operations Dashboard")
        
        if st.session_state['role'] == "Admin": view_df = task_df
        elif st.session_state['role'] == "Manager":
            view_df = task_df[(task_df['Owner'] == st.session_state['user_name']) | (task_df['Reviewer'] == st.session_state['user_name'])]
        else: view_df = task_df[task_df['Owner'] == st.session_state['user_name']]

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
        
        if st.session_state.get("fa_editor") and st.session_state.fa_editor["edited_rows"]:
            task_df.update(edited_df)
            save_data(task_df, TASK_DB)
            st.toast("Auto-saved!", icon="☁️")

    elif choice == "➕ Assign Activity":
        st.title("Assign New Activity")
        with st.form("task_form"):
            client = st.selectbox("Client", client_df['Client_Name'].tolist() if not client_df.empty else ["No Clients"])
            tower = st.selectbox("Tower", ["O2C", "P2P", "R2R"])
            act = st.text_input("Task Description")
            owner = st.selectbox("Action Owner", user_df['Name'].tolist())
            if st.form_submit_button("Publish Task"):
                new_t = pd.DataFrame([{"Date": date.today().strftime("%Y-%m-%d"), "Client": client, "Tower": tower, "Activity": act, "Owner": owner, "Status": "🔴 Pending"}])
                save_data(pd.concat([task_df, new_t], ignore_index=True), TASK_DB)
                st.success("Task Added!")

    elif choice == "🏢 Clients":
        st.title("Client List")
        new_c = st.text_input("Client Name")
        if st.button("Register Client"):
            save_data(pd.concat([client_df, pd.DataFrame([{"Client_Name": new_c}])], ignore_index=True), CLIENT_DB)
            st.rerun()
        st.table(client_df)

    elif choice == "👥 Manage Team":
        st.title("Team Management")
        st.table(user_df[["Name", "Email", "Role"]])

    elif choice == "📅 WD Calendar":
        st.title("Calendar Setup")
        cal_e = st.data_editor(load_data(CALENDAR_DB, ["Date", "Is_Holiday"]), use_container_width=True)
        if st.button("Save Calendar"): save_data(cal_e, CALENDAR_DB)
