import streamlit as st
import pandas as pd
import os
from datetime import datetime, date

# --- 1. CORE CONFIGURATION ---
st.set_page_config(page_title="BGA F&A Portal", layout="wide")

# File Path Constants
USER_DB = "users.csv"
TASK_DB = "database.csv"
CLIENT_DB = "clients.csv"
CALENDAR_DB = "calendar.csv"
LOGO_FILE = "1 BGA Logo Colour.png"

# --- 2. THE BYPASS LOGIN LOGIC ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# LOGIN UI
if not st.session_state['logged_in']:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if os.path.exists(LOGO_FILE):
            st.image(LOGO_FILE, width=200)
        st.title("BGA F&A Portal Login")
        
        with st.form("login_gate"):
            u_email = st.text_input("Email Address").strip().lower()
            u_pass = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign In", use_container_width=True)
            
            if submitted:
                # CRITICAL BYPASS: This check happens before any files are read
                if u_email == "admin@thebga.io" and u_pass == "admin123":
                    st.session_state.update({
                        "logged_in": True,
                        "user_name": "Master Admin",
                        "role": "Admin",
                        "user_email": u_email
                    })
                    st.rerun()
                else:
                    # Secondary check for users in the database
                    if os.path.exists(USER_DB):
                        udf = pd.read_csv(USER_DB)
                        match = udf[udf['Email'].str.lower() == u_email]
                        if not match.empty and str(match.iloc[0]['Password']) == u_pass:
                            st.session_state.update({
                                "logged_in": True,
                                "user_name": match.iloc[0]['Name'],
                                "role": match.iloc[0]['Role'],
                                "user_email": u_email
                            })
                            st.rerun()
                        else:
                            st.error("❌ Invalid Email or Password.")
                    else:
                        st.error("❌ Database not found. Please use Admin Login.")

# --- 3. THE MAIN APPLICATION (POST-LOGIN) ---
else:
    # DATA LOADING UTILITIES
    def load_full_db(file, cols):
        if not os.path.exists(file): return pd.DataFrame(columns=cols)
        df = pd.read_csv(file)
        for c in cols:
            if c not in df.columns: df[c] = ""
        return df

    # LOAD ALL DATA
    task_df = load_full_db(TASK_DB, ["Date", "Client", "Tower", "Activity", "SOP_Link", "Owner", "Reviewer", "Frequency", "WD_Marker", "Status", "Comments"])
    user_df = load_full_db(USER_DB, ["Name", "Email", "Password", "Role", "Manager"])
    client_df = load_full_db(CLIENT_DB, ["Client_Name"])

    # SIDEBAR
    if os.path.exists(LOGO_FILE):
        st.sidebar.image(LOGO_FILE, use_container_width=True)
    st.sidebar.markdown(f"**User:** {st.session_state['user_name']}")
    st.sidebar.markdown(f"**Role:** {st.session_state['role']}")
    
    menu = ["📊 Dashboard", "➕ Assign Activity", "🏢 Clients", "👥 Manage Team"]
    choice = st.sidebar.radio("Navigation", menu)
    
    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.clear()
        st.rerun()

    # --- TAB: DASHBOARD ---
    if choice == "📊 Dashboard":
        st.title("Operations Dashboard")
        
        # Admin sees everything; Users see their own
        if st.session_state['role'] == "Admin":
            display_df = task_df
        else:
            display_df = task_df[task_df['Owner'] == st.session_state['user_name']]

        edited_df = st.data_editor(
            display_df, 
            use_container_width=True,
            column_config={
                "SOP_Link": st.column_config.LinkColumn("🔗 SOP"),
                "Status": st.column_config.SelectboxColumn("Status", options=["🔴 Pending", "🟡 In Progress", "🔍 QC Required", "✅ Approved"])
            }
        )
        
        if st.button("Save Changes", type="primary"):
            # Update master dataframe and save
            task_df.update(edited_df)
            task_df.to_csv(TASK_DB, index=False)
            st.success("✅ Changes successfully saved to Database!")

    # --- TAB: MANAGE TEAM ---
    elif choice == "👥 Manage Team":
        st.title("Team Management")
        with st.form("new_user_form"):
            col1, col2 = st.columns(2)
            new_n = col1.text_input("Full Name")
            new_e = col2.text_input("Email Address")
            new_r = col1.selectbox("Role", ["User", "Manager", "Admin"])
            new_m = col2.selectbox("Manager", ["None"] + user_df['Name'].tolist())
            
            if st.form_submit_button("Register Member"):
                if new_n and new_e:
                    new_row = pd.DataFrame([{"Name": new_n, "Email": new_e, "Role": new_r, "Manager": new_m, "Password": "welcome123"}])
                    updated_users = pd.concat([user_df, new_row], ignore_index=True)
                    updated_users.to_csv(USER_DB, index=False)
                    st.success(f"User {new_n} has been registered!")
                    st.rerun()
                else:
                    st.error("Please fill in Name and Email.")
        
        st.subheader("Active Directory")
        st.dataframe(user_df[["Name", "Email", "Role", "Manager"]], use_container_width=True)

    # --- TAB: CLIENTS ---
    elif choice == "🏢 Clients":
        st.title("Client Master List")
        with st.form("client_entry"):
            c_name = st.text_input("New Client Name")
            if st.form_submit_button("Add Client"):
                if c_name:
                    new_c = pd.DataFrame([{"Client_Name": c_name}])
                    updated_clients = pd.concat([client_df, new_c], ignore_index=True)
                    updated_clients.to_csv(CLIENT_DB, index=False)
                    st.success("Client registered.")
                    st.rerun()
        st.table(client_df)

    # --- TAB: ASSIGN ACTIVITY ---
    elif choice == "➕ Assign Activity":
        st.title("Create New Assignment")
        with st.form("task_entry"):
            t_client = st.selectbox("Client", client_df['Client_Name'].tolist() if not client_df.empty else ["N/A"])
            t_tower = st.selectbox("Tower", ["O2C", "P2P", "R2R"])
            t_desc = st.text_input("Activity Description")
            t_owner = st.selectbox("Owner", user_df['Name'].tolist() if not user_df.empty else ["Admin"])
            
            if st.form_submit_button("Publish Task"):
                new_t = pd.DataFrame([{
                    "Date": date.today().strftime("%Y-%m-%d"),
                    "Client": t_client, "Tower": t_tower, "Activity": t_desc,
                    "Owner": t_owner, "Status": "🔴 Pending"
                }])
                updated_tasks = pd.concat([task_df, new_t], ignore_index=True)
                updated_tasks.to_csv(TASK_DB, index=False)
                st.success("Task Published!")
