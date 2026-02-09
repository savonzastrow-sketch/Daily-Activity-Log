import streamlit as st
import gspread
import pandas as pd
import pytz
import altair as alt
from datetime import datetime

# Initialize the "cache" if it doesn't exist yet
if 'daily_cache' not in st.session_state:
    st.session_state.daily_cache = []

# Function to add to cache - fixed to include the 'Notes' key
def add_to_cache(activity, duration, notes):
    st.session_state.daily_cache.append({
        "Activity": activity, 
        "Mins": duration, 
        "Notes": notes
    })

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
            spreadsheet.share(st.secrets["gcp_service_account"]["client_email"], role='writer', perm_type='user')
            sheet = spreadsheet.sheet1
            
            headers = ["Date", "Satisfaction", "Neuralgia", "Ex1_Type", "Ex1_Mins", "Ex1_Miles", "Ex2_Type", "Ex2_Mins", "Ex2_Miles", "Insights"]
            for i in range(1, 11):
                headers.extend([f"Act{i}_Type", f"Act{i}_Time", f"Act{i}_Text"])
            headers.append("Timestamp")
            sheet.append_row(headers)

        sheet.append_row(entry_data)
        st.success(f"Successfully saved entry for {entry_data[0]}!")

    except Exception as e:
        st.error("Google Sheets Connection Error")
        st.exception(e)

# 3. STREAMLIT UI - INPUT TEMPLATE
st.title("☀️ Daily Activity Log")

with st.form("activity_form", clear_on_submit=True):
    date_val = st.date_input("Date", value=datetime.now())      
    
    st.subheader("Daily Ratings")
    satisfaction = st.select_slider("Satisfaction Rating (1-5)", options=range(1, 6), value=3)
    neuralgia = st.select_slider("Neuralgia/Pain Rating (1-5)", options=range(1, 6), value=1)

    st.divider()

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
    
    activity_options = ["None", "Work", "Meal Prep/clean", "Meal Time", "Maintenance", "Exercise", "Read/Reflect", "Nap/Relax", "Freind Time", "Entertainment", "Work-Calls", "Hobby", "Driving"]
    
    cols = st.columns([1.5, 1, 3.5])
    act_type = cols[0].selectbox("Activity Type", activity_options, key="current_act")
    act_mins = cols[1].number_input("Mins", min_value=0, step=5, key="current_mins")
    act_text = cols[2].text_input("Notes/Details", key="current_notes")

    # Add and Clear buttons inside the form
    btn_col1, btn_col2 = st.columns(2)
    if btn_col1.form_submit_button("Add Activity to List"):
        if act_type != "None":
            add_to_cache(act_type, act_mins, act_text)
            st.rerun()
        else:
            st.warning("Please select an activity type.")

    if btn_col2.form_submit_button("Clear List"):
        st.session_state.daily_cache = []
        st.rerun()
    
    if st.session_state.daily_cache:
        st.write("### Pending Activities")
        st.table(st.session_state.daily_cache)
    
    insights = st.text_area("Daily Insights & Health Notes")
    
    # Final Submission Button
    submit = st.form_submit_button("Save to Google Sheet")

# --- Logic after Submit ---
if submit:
    est = pytz.timezone('US/Eastern')
    timestamp_est = datetime.now(est).strftime("%Y-%m-%d %H:%M:%S")

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

    final_activities = []
    for i in range(10):
        if i < len(st.session_state.daily_cache):
            item = st.session_state.daily_cache[i]
            final_activities.extend([item['Activity'], item['Mins'], item['Notes']])
        else:
            final_activities.extend(["None", 0, ""])

    new_entry.extend(final_activities)
    new_entry.append(timestamp_est)

    log_activity_data(new_entry)
    st.session_state.daily_cache = [] # Clear cache after successful save

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
        df = pd.DataFrame(all_values[1:], columns=all_values[0])
        df['Date'] = pd.to_datetime(df['Date'])
        
        # Numeric conversion
        for col in ['Ex1_Mins', 'Ex2_Mins', 'Satisfaction', 'Neuralgia']:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        df_filtered = df[df['Date'].dt.month_name() == selected_month_name].copy()

        if df_filtered.empty:
            st.info(f"No data logged for {selected_month_name} yet.")
        else:
            # Exercise Chart
            ex1 = df_filtered[['Date', 'Ex1_Type', 'Ex1_Mins']].rename(columns={'Ex1_Type': 'Type', 'Ex1_Mins': 'Mins'})
            ex2 = df_filtered[['Date', 'Ex2_Type', 'Ex2_Mins']].rename(columns={'Ex2_Type': 'Type', 'Ex2_Mins': 'Mins'})
            df_plot = pd.concat([ex1, ex2])
            df_plot = df_plot[df_plot['Type'] != "None"]

            activity_colors = {"Swim": "#72B7B2", "Yoga": "#76A04F", "Run": "#E15759", "Cycle": "#4E79A7", "Elliptical": "#F28E2B", "Strength": "#636363", "Other": "#BAB0AC"}

            st.write("### Exercise Minutes")
            exercise_chart = alt.Chart(df_plot).mark_bar(opacity=0.8).encode(
                x=alt.X('date(Date):O', title=f'Day of {selected_month_name}'),
                y=alt.Y('Mins:Q', aggregate='sum', title='Minutes'),
                color=alt.Color('Type:N', scale=alt.Scale(domain=list(activity_colors.keys()), range=list(activity_colors.values()))),
                tooltip=['Date', 'Type', 'Mins']
            ).properties(height=300)
            st.altair_chart(exercise_chart, use_container_width=True)

            # Health Chart
            st.write("### Satisfaction & Neuralgia Levels")
            health_chart = alt.Chart(df_filtered).transform_fold(
                ['Satisfaction', 'Neuralgia'], as_=['Metric', 'Value']
            ).mark_line(point=True).encode(
                x=alt.X('date(Date):O'),
                y=alt.Y('Value:Q', scale=alt.Scale(domain=[1, 5])),
                color=alt.Color('Metric:N', scale=alt.Scale(range=['#636EFA', '#EF553B'])),
                tooltip=['Date', 'Metric:N', 'Value:Q']
            ).properties(height=250)
            st.altair_chart(health_chart, use_container_width=True)

            # Daily Breakdown Chart
            daily_act_list = []
            for i in range(1, 11):
                temp_df = df_filtered[['Date', f'Act{i}_Type', f'Act{i}_Time']].rename(
                    columns={f'Act{i}_Type': 'Activity', f'Act{i}_Time': 'Mins'}
                )
                daily_act_list.append(temp_df)
            
            df_daily_plot = pd.concat(daily_act_list)
            df_daily_plot = df_daily_plot[df_daily_plot['Activity'] != "None"]
            df_daily_plot['Mins'] = pd.to_numeric(df_daily_plot['Mins'], errors='coerce').fillna(0)

            st.write("### Daily Time Breakdown")
            breakdown_chart = alt.Chart(df_daily_plot).mark_bar().encode(
                x=alt.X('date(Date):O'),
                y=alt.Y('Mins:Q', aggregate='sum'),
                color=alt.Color('Activity:N'),
                tooltip=['Date', 'Activity:N', 'Mins:Q']
            ).properties(height=300)
            st.altair_chart(breakdown_chart, use_container_width=True)

            with st.expander("View Monthly Data Table"):
                st.dataframe(df_filtered.sort_values('Date', ascending=False))
    else:
        st.info("Log some data to see the chart!")

except Exception as e:
    st.error("Error loading chart data.")
    st.exception(e)
