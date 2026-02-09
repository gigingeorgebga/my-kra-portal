import streamlit as st
import pandas as pd
import os
from datetime import datetime, date

# --- 1. CONFIG ---
st.set_page_config(page_title="BGA F&A Portal", layout="wide")

USER_DB, TASK_DB, CLIENT_DB, CALENDAR_DB = "users.csv", "database.csv", "clients.csv", "calendar.csv"
LOGO_FILE = "1 BGA Logo Colour.png"

# --- 2. DATA ENGINE ---
def load_db(file, cols):
    if not os.path.exists(file): return pd.DataFrame(columns=cols)
    df = pd.read_csv(file)
    for c in cols:
        if c not in df.columns: df[c] = ""
    return df

def get_current_wd():
    cal_df = load_db(CALENDAR_DB, ["Date", "Is_Holiday"])
    if cal_df.empty: return "WD Not Set"
    cal_df['Is_Holiday'] = cal_df['Is_Holiday'].astype(str).str.lower() == 'true'
    working_days = cal_df[cal_df['Is_Holiday'] == False].sort_values('Date')
    today_str = date.today().strftime("%Y-%m-%d")
    wd_count = 0
    for _, row in working_days.iterrows():
        wd_count += 1
        if row['Date'] == today_str: return f"WD {wd_count}"
    return "Non-Working Day"

# --- 3. LOGIN & BYPASS ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if os.path.exists(LOGO_FILE): st.image(LOGO_FILE, width=200)
        st.title("BGA F&A Portal Login")
        with st.form("login"):
            u = st.text_input("Email").strip().lower()
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Sign In", use_container_width=True):
                # THE BYPASS
                if u == "admin@thebga.io" and p == "admin123":
                    st.session_state.update({"logged_in": True, "user_name": "Admin", "role": "Admin"})
                    st.rerun()
                else:
                    udf = load_db(USER_DB, ["Name", "Email", "Password", "Role"])
                    match = udf[udf['Email'].str.lower() == u]
                    if not match.empty and str(match.iloc[0]['Password']) == p:
                        st.session_state.update({"logged_in": True, "user_name": match.iloc[0]['Name'], "role": match.iloc[0]['Role']})
                        st.rerun()
                    else: st.error("Invalid Credentials")
else:
    # --- 4. THE COMPLETE APP ---
    task_df = load_db(TASK_DB, ["Date", "Client", "Tower", "Activity", "SOP_Link", "Owner", "Reviewer", "Frequency", "WD_Marker", "Status", "Start_Time", "End_Time", "Comments"])
    user_df = load_db(USER_DB, ["Name", "Email", "Role", "Manager"])
    client_df = load_db(CLIENT_DB, ["Client_Name"])

    if os.path.exists(LOGO_FILE): st.sidebar.image(LOGO_FILE, use_container_width=True)
    st.sidebar.info(f"**Current Context:** {get_current_wd()}")
    
    menu = ["📊 Dashboard", "➕ Assign Activity", "🏢 Clients", "👥 Manage Team", "📅 WD Calendar"]
    choice = st.sidebar.radio("Navigation", menu)
    
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()

    # DASHBOARD
    if choice == "📊 Dashboard":
        st.header("Operations Dashboard")
        view_df = task_df if st.session_state['role'] == "Admin" else task_df[task_df['Owner'] == st.session_state['user_name']]
        
        edited_df = st.data_editor(
            view_df, use_container_width=True,
            column_config={
                "SOP_Link": st.column_config.LinkColumn("🔗 SOP"),
                "Status": st.column_config.SelectboxColumn("Status", options=["🔴 Pending", "🟡 In Progress", "🔍 QC Required", "✅ Approved"]),
                "Start_Time": st.column_config.TimeColumn("Start"),
                "End_Time": st.column_config.TimeColumn("End")
            }
        )
        if st.button("Save Changes"):
            task_df.update(edited_df)
            task_df.to_csv(TASK_DB, index=False)
            st.success("Database Updated!")

    # ASSIGN ACTIVITY (REPLYING ALL FIELDS)
    elif choice == "➕ Assign Activity":
        st.header("New Assignment")
        with st.form("assign"):
            c = st.selectbox("Client", client_df['Client_Name'].tolist() if not client_df.empty else ["N/A"])
            tow = st.selectbox("Tower", ["O2C", "P2P", "R2R"])
            act = st.text_input("Activity")
            sop = st.text_input("SOP Link")
            wdm = st.text_input("WD Marker (e.g., WD 1)")
            own = st.selectbox("Owner", user_df['Name'].tolist())
            if st.form_submit_button("Publish"):
                new_t = pd.DataFrame([{"Date": date.today().strftime("%Y-%m-%d"), "Client": c, "Tower": tow, "Activity": act, "SOP_Link": sop, "WD_Marker": wdm, "Owner": own, "Status": "🔴 Pending"}])
                pd.concat([task_df, new_t], ignore_index=True).to_csv(TASK_DB, index=False)
                st.success("Task Added!")

    # CALENDAR (RESTORED)
    elif choice == "📅 WD Calendar":
        st.header("WD Calendar Setup")
        if st.button("Generate Current Month"):
            import calendar
            today = date.today()
            dates = [date(today.year, today.month, d).strftime("%Y-%m-%d") for d in range(1, calendar.monthrange(today.year, today.month)[1] + 1)]
            pd.DataFrame({"Date": dates, "Is_Holiday": [False]*len(dates)}).to_csv(CALENDAR_DB, index=False)
            st.rerun()
        cal_e = st.data_editor(load_db(CALENDAR_DB, ["Date", "Is_Holiday"]), use_container_width=True)
        if st.button("Save Calendar"):
            cal_e.to_csv(CALENDAR_DB, index=False)
            st.success("Calendar Updated!")
            
    # CLIENTS & TEAM (RESTORED)
    elif choice == "🏢 Clients":
        st.header("Client Master")
        new_c = st.text_input("Client Name")
        if st.button("Add"):
            pd.concat([client_df, pd.DataFrame([{"Client_Name": new_c}])], ignore_index=True).to_csv(CLIENT_DB, index=False)
            st.rerun()
        st.table(client_df)

    elif choice == "👥 Manage Team":
        st.header("Team Management")
        with st.form("team"):
            n = st.text_input("Name")
            e = st.text_input("Email")
            r = st.selectbox("Role", ["User", "Manager", "Admin"])
            if st.form_submit_button("Add Member"):
                pd.concat([user_df, pd.DataFrame([{"Name": n, "Email": e, "Role": r, "Password": "welcome123"}])], ignore_index=True).to_csv(USER_DB, index=False)
                st.rerun()
        st.dataframe(user_df[["Name", "Email", "Role"]])
