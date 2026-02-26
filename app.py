import streamlit as st
import pandas as pd
from supabase import create_client, Client # Added for Supabase
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, date

# --- 1. CONFIGURATION ---
st.set_page_config(
    page_title="BGA F&A Workflow", 
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
    }
)

# This is the "Magic" code that hides the GitHub and Fork icons
st.markdown("""
    <style>
    /* 1. Hide the top bar and main menu */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* 2. Hide the red 'Deploy' crown icon at the top */
    .stAppDeployButton {display: none !important;}
    
    /* 3. Hide the blue 'Manage App' circle at the bottom right */
    [data-testid="stStatusWidget"] {display: none !important;}
    div[data-testid="stToolbar"] {display: none !important;}
    button[title="View source"] {display: none !important;}
    
    /* 4. Final cleanup of any floating icons */
    #stDecoration {display:none !important;}
    </style>
    """, unsafe_allow_html=True)

SENDER_EMAIL = "admin@thebga.io"
SENDER_PASSWORD = "vjec elpd kuvh frqp" 
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
PORTAL_URL = "https://my-team-planner.streamlit.app/"
LOGO_FILE = "1 BGA Logo Colour.png"
CALENDAR_DB = "calendar.csv"

# --- 2. DATA ENGINE (SUPABASE) ---
# This uses the Secrets you just saved
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

def load_data(table_name, cols):
    try:
        # Fetches data from Supabase table
        response = supabase.table(table_name).select("*").execute()
        df = pd.DataFrame(response.data)
        if df.empty:
            return pd.DataFrame(columns=cols)
        # Ensure only requested columns are returned to match your existing logic
        return df[cols] if all(c in df.columns for c in cols) else df
    except Exception as e:
        return pd.DataFrame(columns=cols)

def save_data(df, table_name):
    try:
        # Supabase works best with list of dicts
        data_dict = df.to_dict(orient="records")
        
        # This is the fix: It checks which table we are updating 
        # and uses the correct column name for the cleanup
        if table_name == "users":
            supabase.table(table_name).delete().neq("Email", "0").execute()
        elif table_name == "clients":
            supabase.table(table_name).delete().neq("Client_Name", "0").execute()
        else:
            # For the tasks table
            supabase.table(table_name).delete().neq("Activity", "0").execute()

        supabase.table(table_name).insert(data_dict).execute()
        st.toast(f"✅ {table_name} updated successfully!")
    except Exception as e:
        st.error(f"Save failed to Supabase.")
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

# Load users from Supabase
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
    # --- A. PASSWORD SECURITY CHECK ---
    # This checks if the person logging in still has the default password
    current_user_row = user_df[user_df['Email'].str.lower() == st.session_state['email'].lower()]
    
    if not current_user_row.empty and str(current_user_row.iloc[0]['Password']) == "welcome123":
        st.header("🔐 Reset Temporary Password")
        st.info(f"Hello {st.session_state['user_name']}, for security reasons you must change your password before accessing the portal.")
        
        with st.form("force_reset"):
            new_p = st.text_input("New Password", type="password")
            conf_p = st.text_input("Confirm New Password", type="password")
            if st.form_submit_button("Update & Login"):
                if new_p == conf_p and len(new_p) > 3:
                    user_df.loc[user_df['Email'].str.lower() == st.session_state['email'].lower(), 'Password'] = new_p
                    save_data(user_df, "users")
                    st.success("Password updated! Please wait for refresh...")
                    st.rerun() # <--- THIS IS THE MISSING NUDGE
                    st.rerun() # <--- ADD THIS LINE
                    st.rerun()
                else:
                    st.error("Passwords must match and be at least 4 characters.")
        st.stop() # This "blinds" the rest of the app until they finish

    # --- B. LOAD MAIN DATA ---
    # This only runs if the password check above is passed
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
            if col in display_df.columns:
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
