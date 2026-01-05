import streamlit as st
import gspread
import pandas as pd
import pytz
import altair as alt
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
            headers = ["Date", "Satisfaction", "Neuralgia", "Ex1_Type", "Ex1_Mins", "Ex2_Type", "Ex2_Mins", "Insights", "Timestamp"]
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
    # 1. Get current time in EST
    est = pytz.timezone('US/Eastern')
    timestamp_est = datetime.now(est).strftime("%Y-%m-%d %H:%M:%S")
    
    # 2. Prepare the data row (9 columns)
    new_entry = [
        date_val.strftime("%Y-%m-%d"),
        satisfaction,
        neuralgia,
        ex_type,
        ex_mins,
        ex2_type,
        ex2_mins,
        insights,
        timestamp_est
    ]
    log_activity_data(new_entry)

# --- 4. VISUAL ANALYSIS ---
st.divider()
st.subheader("Visual Analysis")

months = ["January", "February", "March", "April", "May", "June", 
          "July", "August", "September", "October", "November", "December"]
current_month_idx = datetime.now().month - 1
selected_month_name = st.selectbox("Select Month to Review", months, index=current_month_idx)

try:
    client = get_gspread_client()
    sheet = client.open("Daily Activity Log").sheet1
    all_values = sheet.get_all_values()
    
    if len(all_values) > 1:
        # Load into DataFrame using the first row as headers
        df = pd.DataFrame(all_values[1:], columns=all_values[0])
        
        # Convert types so the chart can read them
        df['Date'] = pd.to_datetime(df['Date'])
        df['Ex1_Mins'] = pd.to_numeric(df['Ex1_Mins'], errors='coerce').fillna(0)
        df['Ex2_Mins'] = pd.to_numeric(df['Ex2_Mins'], errors='coerce').fillna(0)
        df['Satisfaction'] = pd.to_numeric(df['Satisfaction'], errors='coerce').fillna(0)
        df['Neuralgia'] = pd.to_numeric(df['Neuralgia'], errors='coerce').fillna(0)

        # Filter for the selected month
        df_filtered = df[df['Date'].dt.month_name() == selected_month_name].copy()

        if df_filtered.empty:
            st.info(f"No data logged for {selected_month_name} yet.")
        else:
            # Prepare data for stacked bars by combining Ex1 and Ex2
            ex1 = df_filtered[['Date', 'Ex1_Type', 'Ex1_Mins']].rename(columns={'Ex1_Type': 'Type', 'Ex1_Mins': 'Mins'})
            ex2 = df_filtered[['Date', 'Ex2_Type', 'Ex2_Mins']].rename(columns={'Ex2_Type': 'Type', 'Ex2_Mins': 'Mins'})
            df_plot = pd.concat([ex1, ex2])
            df_plot = df_plot[df_plot['Type'] != "None"]

            # Define a fixed color map for your activities
            activity_colors = {
                "Swim": "#72B7B2", "Yoga": "#76A04F", "Run": "#E15759", "Cycle": "#4E79A7", "Other": "#BAB0AC"
            }

            # 1. Prepare Exercise Data with a custom label
            bars = alt.Chart(df_plot).transform_calculate(
                # Creates a label like "01-Thu"
                day_label="day(datum.Date) < 10 ? '0' + day(datum.Date) : '' + day(datum.Date)"
            ).mark_bar(opacity=0.7).encode(
                x=alt.X('day_label:O', title=f'Day of {selected_month_name}', sort='ascending'),
                y=alt.Y('Mins:Q', aggregate='sum', title='Exercise Minutes'),
                color=alt.Color('Type:N', scale=alt.Scale(domain=list(activity_colors.keys()), range=list(activity_colors.values()))),
                tooltip=['Date', 'Type', alt.Tooltip('Mins:Q', aggregate='sum')]
            )

            # 2. Prepare Health Data with the SAME custom label
            lines = alt.Chart(df_filtered).transform_calculate(
                day_label="day(datum.Date) < 10 ? '0' + day(datum.Date) : '' + day(datum.Date)"
            ).transform_fold(
                ['Satisfaction', 'Neuralgia'], as_=['Metric', 'Value']
            ).mark_line(point=True).encode(
                x=alt.X('day_label:O', sort='ascending'),
                y=alt.Y('Value:Q', title='Rating (1-5)', scale=alt.Scale(domain=[1, 5])),
                color=alt.Color('Metric:N', scale=alt.Scale(range=['#636EFA', '#EF553B']))
            )

            # 3. Layer them together
            final_chart = alt.layer(bars, lines).resolve_scale(
                y='independent'
            ).properties(height=400)

            st.altair_chart(final_chart, use_container_width=True)

            with st.expander("View Monthly Data Table"):
                st.dataframe(df_filtered.sort_values('Date', ascending=False))
    else:
        st.info("Log some data to see the chart!")

except Exception as e:
    st.error("Error loading chart data.")
    st.exception(e)
