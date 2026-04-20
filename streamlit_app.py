import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Agent Upfront Performance", 
    layout="wide", 
    page_icon="📊"
)

# Custom CSS for better KPI visibility
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 28px; }
    </style>
    """, unsafe_allow_value=True)

st.title("📊 Upfront Sales & Quality Dashboard")
st.markdown("---")

# --- DATA CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1em-FmJ7m5LdyX8Az4ND4HKiFEIg9bCkzEd900e6rEG8/edit#gid=0"

@st.cache_data(ttl=300)  # Refresh every 5 minutes
def load_and_clean_data():
    # Read the data from the synced Google Sheet
    df = conn.read(spreadsheet=SHEET_URL)
    
    # 1. Drop the 'Total' row if it exists in the data to avoid double counting
    df = df[df['Agent'].astype(str).str.upper() != 'TOTAL']
    
    # 2. Clean numeric columns
    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
    
    # 3. Standardize status columns for easier filtering
    status_cols = ['Quality status', 'WlcmStatus', 'Payment Status']
    for col in status_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            
    return df

try:
    df = load_and_clean_data()

    # --- SIDEBAR FILTERS (SIMPLIFIED) ---
    st.sidebar.header("Filter Panel")

    # AGENT FILTER
    all_agents = sorted(df['Agent'].dropna().unique().tolist())
    sel_all_agents = st.sidebar.checkbox("Select All Agents", value=True)
    
    if sel_all_agents:
        selected_agents = st.sidebar.multiselect("Agents", options=all_agents, default=all_agents)
    else:
        selected_agents = st.sidebar.multiselect("Agents", options=all_agents)

    st.sidebar.markdown("---")

    # MONTH FILTER
    all_months = df['Month'].dropna().unique().tolist()
    sel_all_months = st.sidebar.checkbox("Select All Months", value=True)
    
    if sel_all_months:
        selected_months = st.sidebar.multiselect("Months", options=all_months, default=all_months)
    else:
        selected_months = st.sidebar.multiselect("Months", options=all_months)

    # Filter Application
    mask = (df['Agent'].isin(selected_agents)) & (df['Month'].isin(selected_months))
    f_df = df[mask]

    # --- TOP KPI METRICS ---
    st.subheader("Key Performance Indicators")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)

    with kpi1:
        total_revenue = f_df['Amount'].sum()
        st.metric("Total Revenue", f"£{total_revenue:,.2f}")

    with kpi2:
        # Quality Status: Approved
        q_app = len(f_df[f_df['Quality status'].str.lower() == 'approved'])
        st.metric("Quality Approved", q_app)

    with kpi3:
        # Welcome Status: Done
        w_done = len(f_df[f_df['WlcmStatus'].str.lower() == 'done'])
        st.metric("Welcome Done", w_done)

    with kpi4:
        # Payment Status: Accepted
        p_acc = len(f_df[f_df['Payment Status'].str.lower() == 'accepted'])
        st.metric("Payments Accepted", p_acc)

    st.markdown("---")

    # --- AGENT PERFORMANCE BREAKDOWN ---
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.subheader("Revenue by Agent")
        rev_chart = f_df.groupby('Agent')['Amount'].sum().sort_values(ascending=False).reset_index()
        fig_rev = px.bar(
            rev_chart, x='Agent', y='Amount', 
            text_auto='.2s', color='Amount',
            color_continuous_scale='Greens'
        )
        st.plotly_chart(fig_rev, use_container_width=True)

    with col_right:
        st.subheader("Quality Mix")
        q_mix = f_df['Quality status'].value_counts().reset_index()
        fig_pie = px.pie(q_mix, names='Quality status', values='count', hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)

    # --- AGENT PERFORMANCE MATRIX ---
    st.subheader("Agent-Wise Status Matrix")
    
    # Aggregating all statuses by agent
    matrix = f_df.groupby('Agent').agg({
        'Amount': 'sum',
        'Quality status': lambda x: (x.str.lower() == 'approved').sum(),
        'WlcmStatus': lambda x: (x.str.lower() == 'done').sum(),
        'Payment Status': lambda x: (x.str.lower() == 'accepted').sum()
    }).rename(columns={
        'Amount': 'Total Revenue (£)',
        'Quality status': 'Approved (Q)',
        'WlcmStatus': 'Done (W)',
        'Payment Status': 'Accepted (P)'
    }).sort_values(by='Total Revenue (£)', ascending=False).reset_index()

    st.dataframe(matrix, use_container_width=True, hide_index=True)

    # --- SEARCH & EXPORT ---
    with st.expander("🔍 Search Transaction Details"):
        search_query = st.text_input("Search by Customer Name or Phone Number")
        if search_query:
            search_df = f_df[
                (f_df['Customer Name'].str.contains(search_query, case=False, na=False)) |
                (f_df['PhoneNo.'].astype(str).str.contains(search_query, na=False))
            ]
            st.dataframe(search_df, use_container_width=True)
        else:
            st.dataframe(f_df, use_container_width=True)

except Exception as e:
    st.error(f"Something went wrong while loading the dashboard: {e}")
    st.info("Check if your Google Sheet is shared with the Service Account email.")
