import streamlit as st
import pandas as pd
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, date

# --- 1. CONFIGURATION & EMAIL SETTINGS ---
st.set_page_config(page_title="BGA F&A Workflow", layout="wide")

# --- UPDATE THESE FOR EMAILS TO WORK ---
SENDER_EMAIL = "admin@thebga.io" 
SENDER_PASSWORD = "your-16-digit-app-password" 
SMTP_SERVER = "smtp.gmail.com" # Change to smtp.office365.com if using Outlook
SMTP_PORT = 587

USER_DB, TASK_DB, CLIENT_DB, CALENDAR_DB = "users.csv", "database.csv", "clients.csv", "calendar.csv"
LOGO_FILE = "1 BGA Logo Colour.png"

# --- 2. DATA & EMAIL ENGINE ---
def load_db(file, cols):
    if not os.path.exists(file): return pd.DataFrame(columns=cols)
    try:
        df = pd.read_csv(file)
        for c in cols:
            if c not in df.columns: df[c] = ""
        return df
    except:
        return pd.DataFrame(columns=cols)

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

def send_invite_email(recipient_email, recipient_name):
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = recipient_email
        msg['Subject'] = "BGA Portal Invitation"
        body = f"Hello {recipient_name},\n\nYou have been invited to the BGA F&A Workflow Portal.\n\nLogin: {recipient_email}\nTemporary Password: welcome123\n\nPlease login and begin your tasks."
        msg.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, recipient_email, msg.as_string())
        server.quit()
        return True
    except:
        return False

# --- 3. AUTHENTICATION ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

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
    # --- 4. DATA LOADING ---
    task_df = load_db(TASK_DB, ["Date", "Client", "Tower", "Activity", "SOP_Link", "Owner", "Reviewer", "Frequency", "WD_Marker", "Status", "Start_Time", "End_Time", "Comments"])
    user_df = load_db(USER_DB, ["Name", "Email", "Password", "Role", "Manager"])
    client_df = load_db(CLIENT_DB, ["Client_Name"])

    # SIDEBAR
    if os.path.exists(LOGO_FILE): st.sidebar.image(LOGO_FILE, use_container_width=True)
    st.sidebar.info(f"📅 **Current Context:** {get_current_wd()}")
    
    menu = ["📊 Dashboard", "➕ Assign Activity", "🏢 Clients", "👥 Manage Team", "📅 WD Calendar"]
    choice = st.sidebar.radio("Navigation", menu)
    
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()

    # --- TAB: DASHBOARD ---
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
        if st.button("💾 Save Dashboard Changes", type="primary"):
            task_df.update(edited_df)
            task_df.to_csv(TASK_DB, index=False)
            st.success("Database Updated!")

    # --- TAB: ASSIGN ACTIVITY ---
    elif choice == "➕ Assign Activity":
        st.header("Create New Assignment")
        with st.form("assign_form"):
            col1, col2 = st.columns(2)
            c = col1.selectbox("Client", client_df['Client_Name'].tolist() if not client_df.empty else ["No Clients"])
            tow = col2.selectbox("Tower", ["O2C", "P2P", "R2R"])
            act = st.text_input("Activity Description")
            sop = st.text_input("SOP Link (URL)")
            wdm = col1.text_input("WD Marker")
            freq = col2.selectbox("Frequency", ["Daily", "Weekly", "Monthly", "Ad-hoc"])
            own = col1.selectbox("Action Owner", user_df['Name'].tolist() if not user_df.empty else ["Admin"])
            rev = col2.selectbox("Reviewer", user_df['Name'].tolist() if not user_df.empty else ["Admin"])
            
            if st.form_submit_button("Publish Task"):
                new_t = pd.DataFrame([{
                    "Date": date.today().strftime("%Y-%m-%d"), "Client": c, "Tower": tow, 
                    "Activity": act, "SOP_Link": sop, "WD_Marker": wdm, "Frequency": freq,
                    "Owner": own, "Reviewer": rev, "Status": "🔴 Pending"
                }])
                pd.concat([task_df, new_t], ignore_index=True).to_csv(TASK_DB, index=False)
                st.success("Task Published!")

    # --- TAB: MANAGE TEAM (WITH EMAIL TRIGGER) ---
    elif choice == "👥 Manage Team":
        st.header("Team Management")
        with st.form("team_form"):
            col1, col2 = st.columns(2)
            n = col1.text_input("Full Name")
            e = col2.text_input("Email Address")
            r = col1.selectbox("Role", ["User", "Manager", "Admin"])
            m = col2.selectbox("Reporting Manager", ["None"] + user_df['Name'].tolist())
            p = st.text_input("Initial Password", value="welcome123")
            
            if st.form_submit_button("Add Member & Send Invite"):
                if n and e:
                    new_u = pd.DataFrame([{"Name": n, "Email": e, "Role": r, "Manager": m, "Password": p}])
                    pd.concat([user_df, new_u], ignore_index=True).to_csv(USER_DB, index=False)
                    
                    # TRIGGER EMAIL
                    with st.spinner("Sending Invite Email..."):
                        if send_invite_email(e, n):
                            st.success(f"Added {n} and Invite Sent!")
                        else:
                            st.warning(f"Added {n}, but email failed. Check SMTP settings.")
                    st.rerun()
                else: st.error("Name and Email are mandatory.")
        st.dataframe(user_df[["Name", "Email", "Role", "Manager"]], use_container_width=True)

    # --- TAB: WD CALENDAR ---
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

    # --- TAB: CLIENTS ---
    elif choice == "🏢 Clients":
        st.header("Client Master")
        with st.form("client_form"):
            new_c = st.text_input("New Client Name")
            if st.form_submit_button("Add Client"):
                if new_c:
                    pd.concat([client_df, pd.DataFrame([{"Client_Name": new_c}])], ignore_index=True).to_csv(CLIENT_DB, index=False)
                    st.rerun()
        st.table(client_df)
