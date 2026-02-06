import streamlit as st
import pandas as pd
from datetime import datetime

# 1. Page Styling
st.set_page_config(page_title="Team KRA Portal", layout="wide")

# 2. Simple Login (We will make this more advanced later)
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.header("🔑 Team Login")
    user = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Enter Portal"):
        if user == "admin" and password == "team123": # Temporary password
            st.session_state['logged_in'] = True
            st.rerun()
        else:
            st.error("Wrong details. Hint: admin / team123")
else:
    # --- INSIDE THE PORTAL ---
    st.title("📊 Monthly KRA & Ad-hoc Tracker")
    
    # Sidebar for adding new things
    with st.sidebar:
        st.header("➕ Assign New Task")
        t_name = st.text_input("Task Description")
        t_type = st.selectbox("Type", ["Monthly KRA", "Ad-hoc", "QC Follow-up"])
        t_owner = st.selectbox("Assign To", ["John", "Sarah", "Mike", "Me"])
        if st.button("Add to List"):
            st.success("Task assigned successfully!")

    # The Modern List View (Option B)
    st.subheader("Current Work Stream")
    
    # Mock data to show you how it looks
    data = {
        "Owner": ["John", "Sarah", "Mike"],
        "Task": ["Monthly Financials", "Client Onboarding", "System Audit"],
        "Deadline": ["2024-05-30", "2024-05-15", "2024-05-20"],
        "Status": ["🟡 In Progress", "🟢 Completed", "🔴 Pending"],
        "QC Comments": ["N/A", "Approved", "Needs revision"]
    }
    df = pd.DataFrame(data)

    # Displaying the list as a clean table
    st.table(df)

    if st.button("Logout"):
        st.session_state['logged_in'] = False
        st.rerun()
