import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="Team KRA Portal", layout="wide")

# --- 2. LOGO SECTION ---
# This part tries to show the logo but won't crash if it's missing
try:
    st.sidebar.image("logo.png", use_container_width=True)
except:
    st.sidebar.warning("⚠️ Logo file not found in GitHub")
st.sidebar.divider()

# --- 3. THE DATABASE BRAIN ---
DB_FILE = "database.csv"

def load_data():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    # If file is missing, create a blank structure
    return pd.DataFrame(columns=["Date", "Owner", "Task", "Type", "Status", "QC_Comments"])

def save_data(df):
    df.to_csv(DB_FILE, index=False)

# --- 4. SESSION STATE (The Memory) ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# --- 5. LOGIN PAGE LOGIC ---
if not st.session_state['logged_in']:
    st.header("🔑 Team Access Portal")
    
    with st.form("login_form"):
        user_input = st.text_input("Username").lower().strip()
        pass_input = st.text_input("Password", type="password").strip()
        submit_button = st.form_submit_button("Login")

    if submit_button:
        if user_input == "admin" and pass_input == "team123":
            st.session_state['logged_in'] = True
            st.success("Access Granted! Loading...")
            st.rerun()
        else:
            st.error("Invalid Username or Password. Please try again.")

# --- 6. MAIN DASHBOARD (Only shows if logged in) ---
else:
    # Load the latest data from the CSV
    df = load_data()
    
    st.title("📊 Monthly Activity & KRA Planner")
    st.info(f"Welcome back, {st.session_state.get('user', 'Admin')}!")

    # SIDEBAR: ADDING NEW TASKS
    with st.sidebar:
        st.header("➕ Assign New Task")
        with st.form("task_form", clear_on_submit=True):
            new_task = st.text_input("Task Description")
            new_owner = st.selectbox("Assign To", ["Arathi", "Vineeth", "Muaad", "Mili", "Revathy"])
            new_type = st.selectbox("Type", ["Monthly KRA", "Ad-hoc", "Daily Entry"])
            submit = st.form_submit_button("Add Task")
            
            if submit and new_task:
                new_row = pd.DataFrame([{
                    "Date": datetime.now().strftime("%Y-%m-%d"),
                    "Owner": new_owner,
                    "Task": new_task,
                    "Type": new_type,
                    "Status": "🔴 Pending",
                    "QC_Comments": ""
                }])
                df = pd.concat([df, new_row], ignore_index=True)
                save_data(df)
                st.success("Task Added to Database!")
                st.rerun()

    # MAIN AREA: THE MODERN LIST VIEW (Option B)
    st.subheader("📋 Current Work Stream")
    
    # The Interactive Data Editor
    edited_df = st.data_editor(
        df, 
        column_config={
            "Status": st.column_config.SelectboxColumn(
                "Status",
                options=["🔴 Pending", "🟡 In Progress", "🟢 Completed", "QC Required"],
                required=True,
            ),
            "Date": st.column_config.TextColumn(disabled=True), # Don't let users edit the date
        },
        use_container_width=True,
        num_rows="dynamic"
    )

    # SAVE BUTTON
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("💾 Save All Changes"):
            save_data(edited_df)
            st.toast("Progress Saved Successfully!", icon="✅")
    
    with col2:
        if st.button("🚪 Logout"):
            st.session_state['logged_in'] = False
            st.rerun()

    # FOOTER
    st.divider()
    st.caption("KRA Portal v1.0 | Built with Streamlit")
