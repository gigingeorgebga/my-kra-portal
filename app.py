import streamlit as st
import pandas as pd
import os
from datetime import datetime, date

# --- 1. SETTINGS ---
st.set_page_config(page_title="BGA F&A Workflow", layout="wide")

USER_DB, TASK_DB, CALENDAR_DB, CLIENT_DB = "users.csv", "database.csv", "calendar.csv", "clients.csv"
LOGO_FILE = "1 BGA Logo Colour.png"

# --- 2. DATA UTILITIES ---
def load_data(file, columns):
    if not os.path.exists(file):
        return pd.DataFrame(columns=columns)
    try:
        df = pd.read_csv(file)
        for col in columns:
            if col not in df.columns: df[col] = ""
        return df
    except:
        return pd.DataFrame(columns=columns)

def save_data(df, file):
    df.to_csv(file, index=False)

# --- 3. LOGIN LOGIC (FIXED) ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    if os.path.exists(LOGO_FILE):
        st.image(LOGO_FILE, width=200)
    st.title("BGA F&A Portal Login")
    
    with st.container(border=True):
        u_email = st.text_input("Email").strip().lower()
        u_pass = st.text_input("Password", type="password")
        
        if st.button("Sign In", use_container_width=True):
            # STEP 1: Check Master Admin FIRST to bypass empty database issue
            if u_email == "admin@thebga.io" and u_pass == "admin123":
                st.session_state.update({"logged_in": True, "user_name": "Admin", "role": "Admin"})
                st.rerun()
            
            # STEP 2: Check Database for other users
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
                        st.error("Invalid Credentials")
                else:
                    st.error("User Database is empty. Please use Master Admin credentials.")

# --- 4. MAIN APP ---
else:
    # Sidebar
    if os.path.exists(LOGO_FILE):
        st.sidebar.image(LOGO_FILE, use_container_width=True)
    
    st.sidebar.title(f"Hello, {st.session_state['user_name']}")
    menu = ["📊 Dashboard", "➕ Assign Activity", "🏢 Clients", "👥 Manage Team", "📅 WD Calendar"]
    choice = st.sidebar.radio("Navigation", menu)
    
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()

    # Load Data
    user_df = load_data(USER_DB, ["Name", "Email", "Password", "Role", "Manager"])
    task_df = load_data(TASK_DB, ["Date", "Client", "Tower", "Activity", "SOP_Link", "Owner", "Reviewer", "Frequency", "WD_Marker", "Status", "Comments"])
    client_df = load_data(CLIENT_DB, ["Client_Name"])

    if choice == "📊 Dashboard":
        st.header("Operations Dashboard")
        display_df = task_df if st.session_state['role'] == "Admin" else task_df[task_df['Owner'] == st.session_state['user_name']]
        edited_df = st.data_editor(display_df, use_container_width=True)
        if st.button("Save Changes"):
            save_data(edited_df, TASK_DB)
            st.success("Changes Saved!")

    elif choice == "👥 Manage Team":
        st.header("Team Management")
        with st.form("add_user"):
            n = st.text_input("Name")
            e = st.text_input("Email")
            r = st.selectbox("Role", ["User", "Manager", "Admin"])
            if st.form_submit_button("Add Member"):
                new_u = pd.DataFrame([{"Name": n, "Email": e, "Role": r, "Password": "welcome123"}])
                user_df = pd.concat([user_df, new_u], ignore_index=True)
                save_data(user_df, USER_DB)
                st.success(f"User {n} added!")
                st.rerun()
        st.dataframe(user_df[["Name", "Email", "Role"]])
        
    # (Remaining tabs: Clients, Assign Activity, etc.)
