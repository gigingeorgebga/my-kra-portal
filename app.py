import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, date

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="BGA F&A Workflow", layout="wide")

SENDER_EMAIL = "admin@thebga.io"
SENDER_PASSWORD = "vjec elpd kuvh frqp" 
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
PORTAL_URL = "https://my-team-planner.streamlit.app/"
LOGO_FILE = "1 BGA Logo Colour.png"
CALENDAR_DB = "calendar.csv"

# --- 2. DATA ENGINE (GOOGLE SHEETS) ---
# Your specific Sheet ID
SHEET_URL = "https://docs.google.com/spreadsheets/d/1VBNeBZ9nLi8nyNcYIy1ysabsbuSiKKgN8mr-akhh_dg"

conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(worksheet_name, cols):
    try:
        # We point directly to your URL
        df = conn.read(spreadsheet=SHEET_URL, worksheet=worksheet_name, usecols=cols, ttl=0)
        return df
    except Exception as e:
        # Returns empty dataframe if sheet is empty or unreachable
        return pd.DataFrame(columns=cols)

def save_data(df, worksheet_name):
    try:
        # Force the update to your specific sheet
        conn.update(spreadsheet=SHEET_URL, worksheet=worksheet_name, data=df)
        st.toast(f"✅ {worksheet_name} updated successfully!")
    except Exception as e:
        st.error(f"Save failed. Check if Sheet is set to 'Anyone with link can EDIT'")
        st.info(f"Error details: {e}")

# --- 3. HELPER FUNCTIONS ---
def get_current_wd():
    if not os.path.exists(CALENDAR_DB): return "WD Not Set"
    cal_df = pd.read_csv(CALENDAR_DB)
    cal_df['Is_Holiday'] = cal_df['Is_Holiday'].astype(str).str.lower() == 'true'
    working_days = cal_df[cal_df['Is_Holiday'] == False].sort_values('Date')
    today_str = date.today().strftime("%Y-%m-%d")
    wd_count = 0
    for _, row in working_days.iterrows():
        wd_count += 1
        if row['Date'] == today_str: return f"WD {wd_count}"
    return "Non-Working Day"

def send_invite_email(recipient_email, recipient_name):
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = recipient_email
        msg['Subject'] = "BGA Portal Invitation"
        body = f"Hello {recipient_name},\n\nYou have been invited to the BGA F&A Workflow Portal.\n\n🔗 {PORTAL_URL}\n\nUsername: {recipient_email}\nTemporary Password: welcome123"
        msg.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, recipient_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        st.error(f"📧 Email Failed: {str(e)}")
        return False

# --- 4. AUTHENTICATION ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

user_df = load_data("users", cols=["Name", "Email", "Password", "Role", "Manager"])

if not st.session_state['logged_in']:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if os.path.exists(LOGO_FILE): st.image(LOGO_FILE, width=200)
        st.title("BGA Portal Login")
        with st.form("login_gate"):
            u = st.text_input("Email").strip().lower()
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Sign In", use_container_width=True):
                if u == "admin@thebga.io" and p == "admin123":
                    st.session_state.update({"logged_in": True, "user_name": "Admin", "role": "Admin", "email": u})
                    st.rerun()
                else:
                    match = user_df[user_df['Email'].str.lower() == u]
                    if not match.empty and str(match.iloc[0]['Password']) == p:
                        st.session_state.update({"logged_in": True, "user_name": match.iloc[0]['Name'], "role": match.iloc[0]['Role'], "email": u})
                        st.rerun()
                    else:
                        st.error("Invalid Credentials")
else:
    # --- LOAD MAIN DATA ---
    task_df = load_data("tasks", cols=["Date", "Client", "Tower", "Activity", "SOP_Link", "Owner", "Reviewer", "Frequency", "WD_Marker", "Status", "Start_Time", "End_Time", "Comments"])
    client_df = load_data("clients", cols=["Client_Name"])

    # --- SIDEBAR ---
    if os.path.exists(LOGO_FILE): st.sidebar.image(LOGO_FILE, use_container_width=True)
    st.sidebar.info(f"📅 **Context:** {get_current_wd()}")
    
    menu = ["📊 Dashboard", "➕ Assign Activity", "🏢 Clients", "👥 Manage Team", "📅 WD Calendar"] if st.session_state['role'] in ["Admin", "Manager"] else ["📊 Dashboard"]
    choice = st.sidebar.radio("Navigation", menu)
    
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()

    # --- DASHBOARD ---
    if choice == "📊 Dashboard":
        st.header("Operations Dashboard")
        display_df = task_df.copy()
        for col in ["Start_Time", "End_Time"]:
            display_df[col] = pd.to_datetime(display_df[col], errors='coerce').dt.time

        def auto_save():
            edits = st.session_state["dash_editor"]["edited_rows"]
            if edits:
                for index, changes in edits.items():
                    for key, value in changes.items():
                        task_df.at[int(index), key] = value
                save_data(task_df, "tasks")

        current_wd = get_current_wd()
        today_date = date.today().strftime("%Y-%m-%d")
        today_day = date.today().strftime("%A")

        if st.session_state['role'] == "Admin":
            view_df = display_df
        else:
            view_df = display_df[
                (display_df['Owner'] == st.session_state['user_name']) & 
                (
                    (display_df['Frequency'] == "Daily") |
                    (display_df['WD_Marker'] == current_wd) |
                    (display_df['Frequency'] == today_day) | 
                    (display_df['Date'] == today_date)
                )
            ]

        st.data_editor(
            view_df, use_container_width=True, key="dash_editor", on_change=auto_save,
            column_config={
                "SOP_Link": st.column_config.LinkColumn("🔗 SOP"),
                "Status": st.column_config.SelectboxColumn("Status", options=["🔴 Pending", "🟡 In Progress", "🔍 QC Required", "✅ Approved"]),
                "Start_Time": st.column_config.TimeColumn("Start"),
                "End_Time": st.column_config.TimeColumn("End")
            }
        )

    # --- ASSIGN ACTIVITY ---
    elif choice == "➕ Assign Activity":
        st.header("Task Assignment Hub")
        tab1, tab2 = st.tabs(["Manual Entry", "Bulk Upload"])
        with tab1:
            with st.form("assign_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                c_list = client_df['Client_Name'].tolist() if not client_df.empty else ["No Clients"]
                c = col1.selectbox("Client", c_list)
                freq = col2.selectbox("Frequency", ["Daily", "Weekly", "Monthly", "Ad-hoc"])
                wdm, spec_date = "", ""
                if freq == "Monthly": wdm = st.text_input("WD Marker (e.g. WD 1)")
                elif freq == "Weekly": wdm = st.selectbox("Day", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])
                elif freq == "Ad-hoc": spec_date = st.date_input("Date")
                act = st.text_input("Activity Description")
                own = st.selectbox("Action Owner", user_df['Name'].tolist())
                rev = st.selectbox("Reviewer", user_df['Name'].tolist())
                if st.form_submit_button("Publish Task"):
                    new_t = pd.DataFrame([{
                        "Date": str(spec_date) if freq == "Ad-hoc" else date.today().strftime("%Y-%m-%d"), 
                        "Client": c, "Activity": act, "Frequency": freq, "WD_Marker": wdm, 
                        "Owner": own, "Reviewer": rev, "Status": "🔴 Pending"
                    }])
                    save_data(pd.concat([task_df, new_t], ignore_index=True), "tasks")
                    st.rerun()

    # --- CLIENTS ---
    elif choice == "🏢 Clients":
        st.header("Client Master")
        with st.form("c_form"):
            nc = st.text_input("New Client Name")
            if st.form_submit_button("Add Client"):
                if nc:
                    save_data(pd.concat([client_df, pd.DataFrame([{"Client_Name": nc}])], ignore_index=True), "clients")
                    st.rerun()
        st.table(client_df)

    # --- MANAGE TEAM ---
    elif choice == "👥 Manage Team":
        st.header("Team Management")
        with st.form("invite_form"):
            col1, col2 = st.columns(2)
            n = col1.text_input("Name")
            e = col1.text_input("Email")
            r = col2.selectbox("Role", ["User", "Manager", "Admin"])
            m = col2.selectbox("Manager", ["None"] + user_df['Name'].tolist())
            if st.form_submit_button("Invite"):
                new_u = pd.DataFrame([{"Name": n, "Email": e, "Role": r, "Manager": m, "Password": "welcome123"}])
                save_data(pd.concat([user_df, new_u], ignore_index=True), "users")
                send_invite_email(e, n)
                st.rerun()
        st.dataframe(user_df, use_container_width=True)

    # --- WD CALENDAR ---
    elif choice == "📅 WD Calendar":
        st.header("WD Calendar (Local)")
        if st.button("Generate Month"):
            import calendar
            today = date.today()
            dates = [date(today.year, today.month, d).strftime("%Y-%m-%d") for d in range(1, calendar.monthrange(today.year, today.month)[1] + 1)]
            pd.DataFrame({"Date": dates, "Is_Holiday": [False]*len(dates)}).to_csv(CALENDAR_DB, index=False)
            st.rerun()
        if os.path.exists(CALENDAR_DB):
            cal_e = st.data_editor(pd.read_csv(CALENDAR_DB), use_container_width=True)
            if st.button("Save Calendar"):
                cal_e.to_csv(CALENDAR_DB, index=False)
                st.success("Calendar Saved!")
