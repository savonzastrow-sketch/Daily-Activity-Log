import streamlit as st
import gspread
import pandas as pd
from datetime import datetime

# 1. AUTHENTICATION
# This must match your secrets setup
@st.cache_resource
def get_gspread_client():
    # Authenticates using Service Account JSON from Streamlit Secrets
    info = st.secrets["gcp_service_account"]
    client = gspread.service_account_from_dict(info)
    return client

# 2. DATA WRITE FUNCTION
def log_test_data():
    try:
        client = get_gspread_client()

        # Use the key/ID of your sheet (can be ID or Name)
        sheet_name = "Streamlit Test Log" 

        # Open or create the sheet
        try:
                sheet = client.open(sheet_name).sheet1
        except gspread.SpreadsheetNotFound:
                
                # Retrieve the FOLDER_ID from secrets
                folder_id = st.secrets["FOLDER_ID"]
                
                # FIX: Create the spreadsheet explicitly inside the folder
                spreadsheet = client.create(sheet_name, folder_id=folder_id, share_folder=True)
                spreadsheet.share(st.secrets["gcp_service_account"]["client_email"], role='writer', type='user')
                sheet = spreadsheet.sheet1
                sheet.append_row(["Timestamp", "Test Value"])

        # Log the data
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([timestamp, "Success!"])

        st.success(f"Successfully logged data to Google Sheet: {timestamp}")

    except Exception as e:
        st.error("Google Sheets Connection Error")
        st.exception(e)

# 3. STREAMLIT UI
st.title("Google Drive Test App")

if st.button("Log Test Data"):
    log_test_data()

st.caption("If this works, you'll see a new sheet named 'Streamlit Test Log' in your Drive.")
