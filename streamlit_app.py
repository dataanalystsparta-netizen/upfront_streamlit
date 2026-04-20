import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Sparta Telecom Upfront Dashboard", layout="wide", page_icon="📊")

st.title("📊 Upfront Sales & Quality Dashboard")
st.markdown("---")

# --- DATA CONNECTION ---
# Connect to Google Sheets securely
conn = st.connection("gsheets", type=GSheetsConnection)

# Your specific sheet URL
SHEET_URL = "https://docs.google.com/spreadsheets/d/1em-FmJ7m5LdyX8Az4ND4HKiFEIg9bCkzEd900e6rEG8/edit#gid=0"

@st.cache_data(ttl=600) # Caches data for 10 minutes to ensure fast loading
def load_data():
    return conn.read(spreadsheet=SHEET_URL)

try:
    # Load and clean data
    df = load_data()
    
    # Ensure Amount is treated as a number for calculations
    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
    
    # --- SIDEBAR FILTERS ---
    st.sidebar.header("Dashboard Filters")
    
    # Agent Filter
    agents = df['Agent'].dropna().unique().tolist()
    selected_agents = st.sidebar.multiselect("Select Agent", options=agents, default=agents)
    
    # Portal Filter (Sparta / Reliable)
    portals = df['Portal Name'].dropna().unique().tolist()
    selected_portals = st.sidebar.multiselect("Select Portal", options=portals, default=portals)
    
    # Quality Status Filter
    statuses = df['Quality status'].dropna().unique().tolist()
    selected_statuses = st.sidebar.multiselect("Quality Status", options=statuses, default=statuses)

    # Apply Filters
    filtered_df = df[
        (df['Agent'].isin(selected_agents)) & 
        (df['Portal Name'].isin(selected_portals)) &
        (df['Quality status'].isin(selected_statuses))
    ]
    
    # --- TOP KPI METRICS ---
    # We dynamically calculate these based on the active filters
    total_revenue = filtered_df['Amount'].sum()
    total_sales_count = len(filtered_df)
    approved_count = len(filtered_df[filtered_df['Quality status'] == 'Approved'])
    
    col1, col2, col3 = st.columns(3)
    col1.metric(label="Total Revenue", value=f"£{total_revenue:,.2f}")
    col2.metric(label="Total Sales Volume", value=total_sales_count)
    col3.metric(label="Approved Sales", value=approved_count)
    
    st.markdown("---")
    
    # --- VISUALIZATIONS ---
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.subheader("Revenue by Agent")
        if not filtered_df.empty:
            # Group by agent and sum the amounts
            agent_rev = filtered_df.groupby('Agent')['Amount'].sum().reset_index()
            fig_agent = px.bar(agent_rev, x='Agent', y='Amount', color='Agent', text_auto='.2s')
            st.plotly_chart(fig_agent, use_container_width=True)
            
    with col_chart2:
        st.subheader("Sales Volume by Portal")
        if not filtered_df.empty:
            fig_portal = px.pie(filtered_df, names='Portal Name', hole=0.4)
            st.plotly_chart(fig_portal, use_container_width=True)

    # --- DATA GRID ---
    st.subheader("Transaction Details")
    # Display the filtered dataframe
    st.dataframe(filtered_df, use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Unable to connect to data source: {e}")
