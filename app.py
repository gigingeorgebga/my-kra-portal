import streamlit as st
import pandas as pd
import os
from datetime import datetime, date

# --- 1. SETTINGS ---
st.set_page_config(page_title="BGA F&A Workflow", layout="wide")

# File Names
USER_DB = "users.csv"
TASK_DB = "database.csv"
CALENDAR_DB = "calendar.csv"
CLIENT_DB = "clients.csv"
LOGO_FILE = "1 BGA Logo Colour.png"

# --- 2. DATA LOAD/SAVE FUNCTIONS ---
def load_data(file, columns):
    if not os.path.exists(file):
        return pd.DataFrame(columns=columns)
    try:
        df = pd.read_csv(file)
        for col in columns:
            if col not in df.columns:
                df[col] = ""
        return df
    except:
        return pd.DataFrame(columns=columns)

def save_data(df, file):
    df.to_csv(file, index=False)

# --- 3. SESSION STATE (The Login Brain) ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# --- 4. LOGIN PAGE ---
if not st.session_state['logged_in']:
    # Show Logo
    if os.path.exists(LOGO_FILE):
        st.image(LOGO_FILE, width=200)
    
    st.title("BGA F&A Portal Login")
    
    with st.container(border=True):
        u_email = st.text_input("Email").strip().lower()
        u_pass = st.text_input("Password", type="password")
        
        if st.button("Sign In", use_container_width=True):
            # Master Admin Credentials
            if u_email == "admin@thebga.io" and u_pass == "admin123":
                st.session_state.update({"logged_in": True, "user_name": "Admin", "role": "Admin"})
                st.rerun()
            else:
                user_df = load_data(USER_DB, ["Name", "Email", "Password", "Role"])
                if not user_df.empty:
                    match = user_df[user_df['Email'].str.lower() == u_email]
                    if not match.empty and str(match.iloc[0]['Password']) == u_pass:
                        st.session_state.update({
                            "logged_in": True, 
                            "user_name": match.iloc[0]['Name'], 
                            "role": match.iloc[0]['Role']
                        })
                        st.rerun()
                    else:
                        st.error("Invalid Email or Password")
                else:
                    st.error("User Database empty. Use Master Admin login.")

# --- 5. MAIN APP ---
else:
    # Sidebar Navigation
    if os.path.exists(LOGO_FILE):
        st.sidebar.image(LOGO_FILE, use_container_width=True)
    
    st.sidebar.title(f"Welcome, {st.session_state['user_name']}")
    menu = ["📊 Dashboard", "➕ Assign Activity", "🏢 Clients", "👥 Manage Team", "📅 WD Calendar"]
    choice = st.sidebar.radio("Menu", menu)
    
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()

    # Load Databases for the App
    user_df = load_data(USER_DB, ["Name", "Email", "Password", "Role", "Manager"])
    task_df = load_data(TASK_DB, ["Date", "Client", "Tower", "Activity", "SOP_Link", "Owner", "Reviewer", "Frequency", "WD_Marker", "Status", "Comments"])
    client_df = load_data(CLIENT_DB, ["Client_Name"])

    # 📊 DASHBOARD
    if choice == "📊 Dashboard":
        st.header("Operations Dashboard")
        
        # Admin sees all, User sees only theirs
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
        
        if st.button("Save Changes"):
            save_data(edited_df, TASK_DB)
            st.success("Successfully Saved!")

    # 👥 MANAGE TEAM
    elif choice == "👥 Manage Team":
        st.header("Team Management")
        with st.form("add_user_form", clear_on_submit=True):
            n = st.text_input("Full Name")
            e = st.text_input("Email")
            r = st.selectbox("Role", ["User", "Manager", "Admin"])
            m = st.selectbox("Reporting Manager", ["None"] + user_df['Name'].tolist())
            if st.form_submit_button("Add Member"):
                new_row = pd.DataFrame([{"Name": n, "Email": e, "Role": r, "Manager": m, "Password": "welcome123"}])
                user_df = pd.concat([user_df, new_row], ignore_index=True)
                save_data(user_df, USER_DB)
                st.success(f"Added {n}")
                st.rerun()
        st.dataframe(user_df[["Name", "Email", "Role", "Manager"]], use_container_width=True)

    # 🏢 CLIENTS
    elif choice == "🏢 Clients":
        st.header("Client Master")
        with st.form("client_form", clear_on_submit=True):
            c_name = st.text_input("New Client Name")
            if st.form_submit_button("Add Client"):
                new_c = pd.DataFrame([{"Client_Name": c_name}])
                client_df = pd.concat([client_df, new_c], ignore_index=True)
                save_data(client_df, CLIENT_DB)
                st.success("Client Registered")
                st.rerun()
        st.table(client_df)
