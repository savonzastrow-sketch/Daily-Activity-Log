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
            
            headers = ["Date", "Satisfaction", "Neuralgia", "Ex1_Type", "Ex1_Mins", "Ex1_Miles", "Ex2_Type", "Ex2_Mins", "Ex2_Miles", "Insights"]
            # Add the 30 new tracking headers
            for i in range(1, 11):
                headers.extend([f"Act{i}_Type", f"Act{i}_Time", f"Act{i}_Text"])
            headers.append("Timestamp")
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
    date_val = st.date_input("Date", value=datetime.now())      
    
    # 1. Satisfaction & Neuralgia (Full Width)
    st.subheader("Daily Ratings")
    satisfaction = st.select_slider("Satisfaction Rating (1-5)", options=range(1, 6), value=3)
    neuralgia = st.select_slider("Neuralgia/Pain Rating (1-5)", options=range(1, 6), value=1)

    st.divider()

    # 2. Exercise Sections (Split into Columns)
    ex_col1, ex_col2 = st.columns(2)

    with ex_col1:
        st.subheader("Exercise 1")
        ex_type = st.selectbox("Type", ["None", "Swim", "Run", "Cycle", "Yoga", "Elliptical", "Strength", "Other"], key="ex1_type")
        m1_col1, m1_col2 = st.columns(2)
        ex_mins = m1_col1.number_input("Minutes", min_value=0.0, step=5.0, key="ex1_mins")
        ex_miles = m1_col2.number_input("Miles", min_value=0.0, step=0.1, key="ex1_miles")

    with ex_col2:
        st.subheader("Exercise 2")
        ex2_type = st.selectbox("Type", ["None", "Swim", "Run", "Cycle", "Yoga", "Elliptical", "Strength", "Other"], key="ex2_type")
        m2_col1, m2_col2 = st.columns(2)
        ex2_mins = m2_col1.number_input("Minutes", min_value=0.0, step=5.0, key="ex2_mins")
        ex2_miles = m2_col2.number_input("Miles", min_value=0.0, step=0.1, key="ex2_miles")

    st.divider()
    st.subheader("⏰ Daily Time Tracking")
    st.info("Record your activities and durations (in minutes) throughout the day.")

    activity_options = ["None", "Work", "Meal Prep/clean", "Meal Time", "Maintenance", "Exercise", "Read/Reflect", "Nap/Relax", "Freind Time", "Entertainment", "Work-Calls", "Hobby", "Driving"]
    
    # Storage for the 10 rows of activity data
    daily_activities = []

    # Using a loop to create 10 full-width rows
    for i in range(1, 11):
        # Adjusted column ratios to give more space to Notes/Details
        cols = st.columns([1.5, 1, 3.5]) 
        act_type = cols[0].selectbox(f"Activity {i}", activity_options, key=f"act_type_{i}")
        # Changed to number_input for minutes
        act_mins = cols[1].number_input("Mins", min_value=0, step=5, key=f"act_time_{i}") 
        act_text = cols[2].text_input("Notes/Details", key=f"act_text_{i}", placeholder="What did you accomplish?")
        daily_activities.extend([act_type, act_mins, act_text])
    
    insights = st.text_area("Daily Insights & Health Notes")
    
    submit = st.form_submit_button("Save to Google Sheet")

if submit:
    # 1. Get current time in EST
    est = pytz.timezone('US/Eastern')
    timestamp_est = datetime.now(est).strftime("%Y-%m-%d %H:%M:%S")
    
    # Prepare the base data row
    new_entry = [
        date_val.strftime("%Y-%m-%d"),
        satisfaction,
        neuralgia,
        ex_type,
        ex_mins,
        ex_miles,
        ex2_type,
        ex2_mins,
        ex2_miles,
        insights
    ]
    
    # Append the 30 activity tracking fields
    new_entry.extend(daily_activities)
    
    # Add final timestamp
    new_entry.append(timestamp_est)
    
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

            # 1. Fixed Activity Colors
            activity_colors = {
                "Swim": "#72B7B2", "Yoga": "#76A04F", "Run": "#E15759", "Cycle": "#4E79A7", "Elliptical": "#F28E2B", "Strength": "#808080", "Other": "#BAB0AC"
            }

            # --- CHART 1: EXERCISE (Stacked Bar) ---
            st.write("### Exercise Minutes")
            exercise_chart = alt.Chart(df_plot).mark_bar(opacity=0.8).encode(
                x=alt.X('date(Date):O', title=f'Day of {selected_month_name}'),
                y=alt.Y('Mins:Q', aggregate='sum', title='Minutes'),
                color=alt.Color('Type:N', 
                    title='Activity', 
                    scale=alt.Scale(domain=list(activity_colors.keys()), range=list(activity_colors.values()))
                ),
                tooltip=['Date', 'Type', alt.Tooltip('Mins:Q', aggregate='sum', title='Total Mins')]
            ).properties(height=300)
            
            st.altair_chart(exercise_chart, use_container_width=True)

            # --- CHART 2: HEALTH METRICS (Lines) ---
            st.write("### Satisfaction & Neuralgia Levels")
            health_chart = alt.Chart(df_filtered).transform_fold(
                ['Satisfaction', 'Neuralgia'], 
                as_=['Metric', 'Value']
            ).mark_line(point=True).encode(
                x=alt.X('date(Date):O', title=f'Day of {selected_month_name}'),
                y=alt.Y('Value:Q', title='Rating (1-5)', scale=alt.Scale(domain=[1, 5])),
                color=alt.Color('Metric:N',  # <--- Added :N here to fix the ValueError
                    title='Metric',
                    scale=alt.Scale(range=['#636EFA', '#EF553B'])
                ),
                tooltip=['Date', 'Metric:N', 'Value:Q']
            ).properties(height=250)

            st.altair_chart(health_chart, use_container_width=True)

            with st.expander("View Monthly Data Table"):
                st.dataframe(df_filtered.sort_values('Date', ascending=False))
    else:
        st.info("Log some data to see the chart!")

except Exception as e:
    st.error("Error loading chart data.")
    st.exception(e)
