import streamlit as st
import gspread
import pandas as pd
from datetime import datetime

# 1. AUTHENTICATION
@st.cache_resource
def get_gspread_client():
    info = st.secrets["gcp_service_account"]
    client = gspread.service_account_from_dict(info)
    return client

# 2. DATA WRITE FUNCTION
def log_activity_data(entry_data):
    try:
        client = get_gspread_client()
        sheet_name = "Daily Activity Log" 

        # Open or create the sheet
        try:
            spreadsheet = client.open(sheet_name)
            sheet = spreadsheet.sheet1
        except gspread.SpreadsheetNotFound:
            folder_id = st.secrets["FOLDER_ID"]
            spreadsheet = client.create(sheet_name, folder_id=folder_id)
            # Share with your service account email to ensure edit access
            spreadsheet.share(st.secrets["gcp_service_account"]["client_email"], role='writer', perm_type='user')
            sheet = spreadsheet.sheet1
            
            # Create Headers based on your fields
            headers = ["Date", "Satisfaction", "Neuralgia", "Exercise_Type", "Exercise_Mins", "Insights"]
            sheet.append_row(headers)

        # Log the data row
        sheet.append_row(entry_data)
        st.success(f"Successfully saved entry for {entry_data[0]}!")

    except Exception as e:
        st.error("Google Sheets Connection Error")
        st.exception(e)

# 3. STREAMLIT UI - INPUT TEMPLATE
st.title("☀️ Daily Activity Log")
st.write("Record your health metrics and exercise for today.")

with st.form("activity_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    
    with col1:
        date_val = st.date_input("Date", datetime.now())
        satisfaction = st.slider("Satisfaction Rating (1-5)", 1, 5, 3)
        neuralgia = st.slider("Neuralgia/Pain Rating (1-5)", 1, 5, 1)
        
    with col2:
        st.subheader("Exercise 1")
        ex_type = st.selectbox("Type", ["None", "Swim", "Run", "Cycle", "Yoga", "Other"], key="ex1_type")
        ex_mins = st.number_input("Minutes", min_value=0.0, step=5.0, key="ex1_mins")
        
        st.divider()
        
        st.subheader("Exercise 2")
        ex2_type = st.selectbox("Type", ["None", "Swim", "Run", "Cycle", "Yoga", "Other"], key="ex2_type", index=0)
        ex2_mins = st.number_input("Minutes", min_value=0.0, step=5.0, key="ex2_mins")
    
    insights = st.text_area("Daily Insights & Health Notes")
    
    submit = st.form_submit_button("Save to Google Sheet")

if submit:
    # Prepare the data row with 8 columns total
    new_entry = [
        date_val.strftime("%Y-%m-%d"),
        satisfaction,
        neuralgia,
        ex_type,
        ex_mins,
        ex2_type,
        ex2_mins,
        insights
    ]
    log_activity_data(new_entry)

# --- 4. FUTURE STEP: VIEW DATA ---
st.divider()
if st.checkbox("Show recent log entries"):
    try:
        client = get_gspread_client()
        sheet = client.open("Daily Activity Log").sheet1
        data = sheet.get_all_records()
        if data:
            st.dataframe(pd.DataFrame(data).tail(10))
        else:
            st.info("The sheet is currently empty.")
    except:
        st.info("No data found yet. Save your first entry to see the log.")
