import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Agent Performance Dashboard", layout="wide", page_icon="📈")

st.title("📈 Agent-Wise Status & Revenue Dashboard")
st.markdown("---")

# --- DATA CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1em-FmJ7m5LdyX8Az4ND4HKiFEIg9bCkzEd900e6rEG8/edit#gid=0"

@st.cache_data(ttl=300) # Refresh data every 5 minutes
def load_data():
    data = conn.read(spreadsheet=SHEET_URL)
    # Remove the 'Total' row from raw data to prevent double-counting in aggregations
    data = data[data['Agent'].str.upper() != 'TOTAL']
    # Ensure Amount is numeric
    data['Amount'] = pd.to_numeric(data['Amount'], errors='coerce').fillna(0)
    return data

try:
    df = load_data()

    # --- SIDEBAR FILTERS ---
    st.sidebar.header("Filters")
    
    # Agent Filter
    agents = sorted(df['Agent'].dropna().unique().tolist())
    selected_agents = st.sidebar.multiselect("Select Agent", options=agents, default=agents)
    
    # Month Filter
    months = df['Month'].dropna().unique().tolist()
    selected_months = st.sidebar.multiselect("Select Month", options=months, default=months)

    # Filtered Dataframe
    f_df = df[(df['Agent'].isin(selected_agents)) & (df['Month'].isin(selected_months))]

    # --- TOP KPI METRICS (4 Columns) ---
    col1, col2, col3, col4 = st.columns(4)

    # 1. Total Revenue
    total_rev = f_df['Amount'].sum()
    col1.metric("Total Revenue", f"£{total_rev:,.2f}")

    # 2. Quality Status (Focus on 'Approved')
    q_approved = len(f_df[f_df['Quality status'].str.contains('Approved', na=False, case=False)])
    col2.metric("Quality Approved", q_approved)

    # 3. Welcome Status (Focus on 'Done' or 'Approved')
    w_done = len(f_df[f_df['WlcmStatus'].str.contains('Done', na=False, case=False)])
    col3.metric("Welcome Done", w_done)

    # 4. Payment Status (Focus on 'Accepted')
    p_accepted = len(f_df[f_df['Payment Status'].str.contains('Accepted', na=False, case=False)])
    col4.metric("Payments Accepted", p_accepted)

    st.markdown("---")

    # --- AGENT-WISE BREAKDOWN CHARTS ---
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.subheader("Revenue by Agent")
        rev_by_agent = f_df.groupby('Agent')['Amount'].sum().sort_values(ascending=False).reset_index()
        fig_rev = px.bar(rev_by_agent, x='Agent', y='Amount', text_auto='.2s', color_discrete_sequence=['#00CC96'])
        st.plotly_chart(fig_rev, use_container_width=True)

    with chart_col2:
        st.subheader("Quality Status Distribution")
        # Breakdown of different quality statuses (Approved, Cancelled, etc.)
        q_dist = f_df['Quality status'].value_counts().reset_index()
        fig_q = px.pie(q_dist, names='Quality status', values='count', hole=0.4)
        st.plotly_chart(fig_q, use_container_width=True)

    # --- DETAILED AGENT STATUS TABLE ---
    st.subheader("Agent Performance Matrix")
    
    # Create a pivot-style summary for each agent
    agent_summary = f_df.groupby('Agent').agg({
        'Amount': 'sum',
        'Quality status': lambda x: (x == 'Approved').sum(),
        'WlcmStatus': lambda x: (x == 'Done').sum(),
        'Payment Status': lambda x: (x == 'Accepted').sum()
    }).rename(columns={
        'Amount': 'Total Revenue',
        'Quality status': 'Approved (Quality)',
        'WlcmStatus': 'Done (Welcome)',
        'Payment Status': 'Accepted (Payment)'
    }).reset_index()

    st.dataframe(agent_summary, use_container_width=True, hide_index=True)

    # --- FULL DATA VIEW ---
    with st.expander("View Raw Filtered Transactions"):
        st.dataframe(f_df, use_container_width=True)

except Exception as e:
    st.error(f"Error loading dashboard: {e}")
