import streamlit as st
import gspread
import pandas as pd
import pytz
import altair as alt
from datetime import datetime

# --- 1. AUTHENTICATION ---
@st.cache_resource
def get_gspread_client():
    info = st.secrets["gcp_service_account"]
    client = gspread.service_account_from_dict(info)
    return client

# --- 2. DATA WRITE FUNCTIONS ---
def add_to_temp_storage(activity, duration, notes):
    """Saves a single activity row to the Temp_Activities tab for persistence."""
    try:
        client = get_gspread_client()
        temp_sheet = client.open("Daily Activity Log").worksheet("Temp_Activities")
        temp_sheet.append_row([activity, duration, notes])
    except Exception as e:
        st.error(f"Error saving to temporary storage: {e}")

def log_activity_data(entry_data):
    """Saves the final combined daily entry to the main Master tab."""
    try:
        client = get_gspread_client()
        spreadsheet = client.open("Daily Activity Log")
        sheet = spreadsheet.sheet1
        sheet.append_row(entry_data)
        st.success(f"Successfully saved entry for {entry_data[0]}!")
    except Exception as e:
        st.error(f"Google Sheets Connection Error: {e}")

# --- 3. UI - DAILY TIME TRACKING (PERSISTENT) ---
st.title("☀️ Daily Activity Log")

st.divider()
st.subheader("⏰ Daily Time Tracking")

# Fixed Color Palette for Consistency
activity_colors = {
    "Swim": "#72B7B2", "Yoga": "#76A04F", "Run": "#E15759", 
    "Cycle": "#4E79A7", "Elliptical": "#F28E2B", "Strength": "#636363", "Other": "#BAB0AC"
}

activity_options = ["None", "Work", "Meal Prep/clean", "Meal Time", "Maintenance", "Exercise", "Read/Reflect", "Nap/Relax", "Friend Time", "Entertainment", "Work-Calls", "Hobby", "Driving"]

cols = st.columns([1.5, 1, 3.5])
act_type = cols[0].selectbox("Activity Type", activity_options, key="ui_act_type")
act_mins = cols[1].number_input("Mins", min_value=0, step=5, key="ui_act_mins")
act_text = cols[2].text_input("Notes/Details", key="ui_act_notes")

btn_col1, btn_col2 = st.columns(2)

if btn_col1.button("Add Activity to List"):
    if act_type != "None":
        add_to_temp_storage(act_type, act_mins, act_text)
        st.rerun()
    else:
        st.warning("Please select an activity type.")

if btn_col2.button("Clear List"):
    try:
        client = get_gspread_client()
        temp_sheet = client.open("Daily Activity Log").worksheet("Temp_Activities")
        temp_sheet.batch_clear(['A2:C100'])
        st.rerun()
    except Exception as e:
        st.error(f"Error clearing temporary storage: {e}")

# --- DISPLAY CURRENT CLOUD PENDING LIST ---
try:
    client = get_gspread_client()
    temp_sheet = client.open("Daily Activity Log").worksheet("Temp_Activities")
    temp_rows = temp_sheet.get_all_values()
    
    if len(temp_rows) > 1:
        st.write("### 📝 Pending Activities (Stored in Cloud)")
        pending_df = pd.DataFrame(temp_rows[1:], columns=temp_rows[0])
        st.dataframe(pending_df, use_container_width=True)
    else:
        st.info("No pending activities. Add one above to get started!")
except:
    st.info("Cloud storage ready for your first activity.")

# --- 4. MAIN FORM (RATINGS & EXERCISES) ---
with st.form("main_activity_form", clear_on_submit=True):
    date_val = st.date_input("Date", value=datetime.now())      
    
    st.subheader("Daily Ratings")
    satisfaction = st.select_slider("Satisfaction Rating (1-5)", options=range(1, 6), value=3)
    neuralgia = st.select_slider("Neuralgia/Pain Rating (1-5)", options=range(1, 6), value=1)

    st.divider()

    ex_col1, ex_col2 = st.columns(2)
    with ex_col1:
        st.subheader("Exercise 1")
        ex1_type = st.selectbox("Type", ["None", "Swim", "Run", "Cycle", "Yoga", "Elliptical", "Strength", "Other"], key="ex1_sel")
        m1_col1, m1_col2 = st.columns(2)
        ex1_mins = m1_col1.number_input("Minutes", min_value=0.0, step=5.0, key="ex1_m")
        ex1_miles = m1_col2.number_input("Miles", min_value=0.0, step=0.1, key="ex1_mi")

    with ex_col2:
        st.subheader("Exercise 2")
        ex2_type = st.selectbox("Type", ["None", "Swim", "Run", "Cycle", "Yoga", "Elliptical", "Strength", "Other"], key="ex2_sel")
        m2_col1, m2_col2 = st.columns(2)
        ex2_mins = m2_col1.number_input("Minutes", min_value=0.0, step=5.0, key="ex2_m")
        ex2_miles = m2_col2.number_input("Miles", min_value=0.0, step=0.1, key="ex2_mi")
    
    insights = st.text_area("Daily Insights & Health Notes", key="main_insights")
    
    submit = st.form_submit_button("Save to Google Sheet")

# --- 5. LOGIC AFTER SUBMIT ---
if submit:
    est = pytz.timezone('US/Eastern')
    timestamp_est = datetime.now(est).strftime("%Y-%m-%d %H:%M:%S")

    client = get_gspread_client()
    temp_sheet = client.open("Daily Activity Log").worksheet("Temp_Activities")
    temp_rows = temp_sheet.get_all_values()[1:] 

    new_entry = [
        date_val.strftime("%Y-%m-%d"),
        satisfaction,
        neuralgia,
        ex1_type, ex1_mins, ex1_miles,
        ex2_type, ex2_mins, ex2_miles,
        insights
    ]

    final_activities = []
    for i in range(10):
        if i < len(temp_rows):
            row = temp_rows[i]
            final_activities.extend([row[0], row[1], row[2]])
        else:
            final_activities.extend(["None", 0, ""])

    new_entry.extend(final_activities)
    new_entry.append(timestamp_est)

    log_activity_data(new_entry)
    temp_sheet.batch_clear(['A2:C100'])
    st.rerun()

# --- 6. VISUAL ANALYSIS ---
st.divider()
st.subheader("Visual Analysis")

try:
    client = get_gspread_client()
    sheet = client.open("Daily Activity Log").sheet1
    all_values = sheet.get_all_values()
    
    if len(all_values) > 1:
        df = pd.DataFrame(all_values[1:], columns=all_values[0])
        df['Date'] = pd.to_datetime(df['Date'])
        
        for col in ['Ex1_Mins', 'Ex2_Mins', 'Satisfaction', 'Neuralgia']:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        selected_month = st.selectbox("Select Month to Review", months, index=datetime.now().month - 1)
        df_filtered = df[df['Date'].dt.month_name() == selected_month].copy()

        if not df_filtered.empty:
            st.write("### Exercise Minutes")
            ex1_sub = df_filtered[['Date', 'Ex1_Type', 'Ex1_Mins']].rename(columns={'Ex1_Type': 'Type', 'Ex1_Mins': 'Mins'})
            ex2_sub = df_filtered[['Date', 'Ex2_Type', 'Ex2_Mins']].rename(columns={'Ex2_Type': 'Type', 'Ex2_Mins': 'Mins'})
            df_plot = pd.concat([ex1_sub, ex2_sub])
            df_plot = df_plot[df_plot['Type'] != "None"]
            
            # FIXED SYNTAX ERROR HERE
            exercise_chart = alt.Chart(df_plot).mark_bar().encode(
                x='date(Date):O', 
                y='sum(Mins):Q', 
                color=alt.Color('Type:N', scale=alt.Scale(domain=list(activity_colors.keys()), range=list(activity_colors.values())))
            ).properties(height=300)
            st.altair_chart(exercise_chart, use_container_width=True)

            st.write("### Satisfaction & Neuralgia Levels")
            health_chart = alt.Chart(df_filtered).transform_fold(
                ['Satisfaction', 'Neuralgia'], as_=['Metric', 'Value']
            ).mark_line(point=True).encode(
                x='date(Date):O', 
                y=alt.Y('Value:Q', scale=alt.Scale(domain=[1, 5])),
                color=alt.Color('Metric:N', scale=alt.Scale(range=['#636EFA', '#EF553B']))
            ).properties(height=250)
            st.altair_chart(health_chart, use_container_width=True)

            st.write("### 📜 Past Activity Details")
            hist_list = []
            for i in range(1, 11):
                temp = df_filtered[['Date', f'Act{i}_Type', f'Act{i}_Time', f'Act{i}_Text']].rename(
                    columns={f'Act{i}_Type': 'Activity', f'Act{i}_Time': 'Mins', f'Act{i}_Text': 'Notes'}
                )
                hist_list.append(temp)
            df_hist = pd.concat(hist_list)
            df_hist = df_hist[df_hist['Activity'] != "None"]
            st.dataframe(df_hist.sort_values('Date', ascending=False), use_container_width=True)

except Exception as e:
    st.info("Log your daily data to unlock historical charts and tables!")
