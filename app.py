import streamlit as st
import pandas as pd
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, date

# --- 1. CONFIG ---
st.set_page_config(page_title="BGA F&A Workflow", layout="wide")

# EMAIL SETTINGS (Update these to your BGA credentials)
SENDER_EMAIL = "your-admin-email@gmail.com" 
SENDER_PASSWORD = "your-app-password" 
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# --- 2. DATA UTILITIES ---
USER_DB, TASK_DB, CALENDAR_DB, CLIENT_DB = "users.csv", "database.csv", "calendar.csv", "clients.csv"
LOGO_FILE = "1 BGA Logo Colour.png" # Ensure this matches your file name exactly

def load_data(file, columns):
    if not os.path.exists(file): return pd.DataFrame(columns=columns)
    df = pd.read_csv(file)
    for col in columns:
        if col not in df.columns: df[col] = ""
    return df

def save_data(df, file):
    df.to_csv(file, index=False)

# --- 3. AUTH & SESSION ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    # --- LOGIN PAGE LOGO ---
    if os.path.exists(LOGO_FILE):
        st.image(LOGO_FILE, width=200)
    else:
        st.title("BGA") # Fallback text if logo is missing
        
    st.title("F&A Portal Login")
    u_email = st.text_input("Email").strip().lower()
    u_pass = st.text_input("Password", type="password").strip()
    if st.button("Sign In"):
        if u_email == "admin@thebga.io" and u_pass == "admin123":
            st.session_state.update({"logged_in": True, "user_name": "Admin", "role": "Admin"})
            st.rerun()
        # (Add standard login database check here)
else:
    # --- APP SIDEBAR LOGO ---
    if os.path.exists(LOGO_FILE):
        st.sidebar.image(LOGO_FILE, use_container_width=True)
    
    st.sidebar.title("BGA F&A")
    # ... rest of your navigation logic ...
