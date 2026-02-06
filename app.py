import streamlit as st
import pandas as pd
from datetime import datetime
import os

# 1. Page Config & Logo
st.set_page_config(page_title="Team KRA Portal", layout="wide")
st.sidebar.image("logo.png", use_container_width=True) # Ensure your logo filename matches!
st.sidebar.title("Navigation")

# 2. THE BRAIN: Function to load and save data
DB_FILE = "database.csv"

def load_data():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=["Date", "Owner", "Task", "Type", "Status", "QC_Comments"])

def save_data(df):
    df.to_csv(DB_FILE, index=False)

# 3. Secure Login
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.header("🔑 Team Access")
    user = st.text_input("Username")
    pw = st.text_input("Password", type="password")
    if st.button("Login"):
        if user == "admin" and pw == "team123":
            st.session_state['logged_in'] = True
            st.rerun()
else:
    # --- LOGGED IN AREA ---
    df = load_data()
    
    st.title("📊 Monthly Activity & KRA Planner")

    # Sidebar: Adding New Tasks
    with st.sidebar:
        st.subheader("➕ Assign New Task")
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
                st.success("Added!")
                st.rerun()

    # Main Page: The Modern List View
    st.subheader("📋 Team Work-Stream")
    
    # This creates the "Interactive Table" where people can update status
    edited_df = st.data_editor(
        df, 
        column_config={
            "Status": st.column_config.SelectboxColumn(
                "Status",
                options=["🔴 Pending", "🟡 In Progress", "🟢 Completed", "QC Required"],
                required=True,
            )
        },
        use_container_width=True,
        num_rows="dynamic"
    )

    if st.button("💾 Save All Changes"):
        save_data(edited_df)
        st.toast("Progress Saved Successfully!", icon="✅")

    if st.button("Logout"):
        st.session_state['logged_in'] = False
        st.rerun()
