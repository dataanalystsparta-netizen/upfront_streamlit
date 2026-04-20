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
    """, unsafe_allow_html=True)

st.title("📊 Upfront Sales & Quality Dashboard")
st.markdown("---")

# --- DATA CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)
# UPDATED NEW SHEET URL
SHEET_URL = "https://docs.google.com/spreadsheets/d/1uX9RrW7Z5ru4ljdK2D1os5Ao5KEBxkihMTDv6MVmzlQ/edit?gid=0#gid=0"

@st.cache_data(ttl=300)
def load_and_clean_data():
    df = conn.read(spreadsheet=SHEET_URL)
    # Exclude total rows
    df = df[df['Agent'].astype(str).str.upper() != 'TOTAL']
    # Convert Amount to numeric
    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)

    # --- QUALITY STATUS CLEANUP ---
    if 'Quality status' in df.columns:
        df['Quality status'] = df['Quality status'].astype(str).str.strip()
        
        quality_map = {
            'passed': 'Approved',
            'Passed': 'Approved',
            'approved': 'Approved',
            'Approved': 'Approved',
            'Rejected': 'Quality Rejected',
            'Rejectet': 'Quality Rejected',
            'Cancelled':'Quality Cancelled',
            'Quality rejected': 'Quality Rejected',
            'Quality Rejected': 'Quality Rejected',
            'Qulaity rejected': 'Quality Rejected',
            'Qulality rejected': 'Quality Rejected',
            'Quality cancelled': 'Quality Cancelled',
            'Quality Cancelled': 'Quality Cancelled',
            'Quality canclled': 'Quality Cancelled',
            'Qulaity cancelled': 'Quality Cancelled',
            'Qulality cancelled': 'Quality Cancelled',
            'Cancel':'Quality Cancelled',
            'cancelled': 'Quality Cancelled',
            'Rework':'Rework Required',
            'Rework required':'Rework Required',
            'Rewok required':'Rework Required',
            'Rejected/Rwork':'Quality Rejected',
            'Cx is not interested':'Quality Cancelled',
            'Son Got the POA':'Quality Cancelled',
            'Duplicate/Rejected':'Duplicate',
            'Hold': 'Hold',
            'HOld': 'Hold',
            'hold':'Hold',
            'Duplicate': 'Duplicate',
            'Dupliate': 'Duplicate'
        }
        df['Quality status'] = df['Quality status'].replace(quality_map)

    # --- CANCELLATION REASON CLEANUP ---
    if 'Reason of cancellation' in df.columns:
        df['Reason of cancellation'] = df['Reason of cancellation'].astype(str).str.strip()
        
        reason_map = {
            'Family interference': 'Family Interference',
            'Family Interference': 'Family Interference',
            'Inbound cancel': 'Inbound Cancel',
            'Inbound Cancel': 'Inbound Cancel',
            'Improper sale': 'Improper Sale',
            'Not for sale': 'Not For Sale',
            'Invalid account details': 'Invalid Account Details',
            'Not intersted': 'Not Interested',  # Fix typo from sample data
            'nan': 'N/A',
            'None': 'N/A',
            '': 'N/A'
        }
        df['Reason of cancellation'] = df['Reason of cancellation'].replace(reason_map)
        df['Reason of cancellation'] = df['Reason of cancellation'].str.title().replace('N/A', 'N/A')

    # Standardize other columns
    for col in ['Welcome Status', 'Payment Status', 'Month']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            
    return df

try:
    df = load_and_clean_data()

    # --- SIDEBAR FILTERS ---
    st.sidebar.header("Filter Panel")
    
    # 1. AGENT FILTER
    st.sidebar.subheader("👤 Agent Filter")
    all_agents = sorted(df['Agent'].dropna().unique().tolist())
    agent_mode = st.sidebar.radio("Agent Mode:", ["Include", "Exclude"], horizontal=True)
    selected_agents = st.sidebar.multiselect("Select Agents:", options=all_agents, placeholder="Showing All Agents...")

    # 2. MONTH FILTER
    st.sidebar.subheader("📅 Month Filter")
    all_months = df['Month'].dropna().unique().tolist() if 'Month' in df.columns else []
    month_mode = st.sidebar.radio("Month Mode:", ["Include", "Exclude"], horizontal=True)
    selected_months = st.sidebar.multiselect("Select Months:", options=all_months, placeholder="Showing All Months...")

    # --- APPLY FILTER LOGIC ---
    f_df = df.copy()

    if selected_agents:
        if agent_mode == "Include":
            f_df = f_df[f_df['Agent'].isin(selected_agents)]
        else:
            f_df = f_df[~f_df['Agent'].isin(selected_agents)]

    if selected_months:
        if month_mode == "Include":
            f_df = f_df[f_df['Month'].isin(selected_months)]
        else:
            f_df = f_df[~f_df['Month'].isin(selected_months)]

    # --- TOP KPI METRICS ---
    st.subheader("Key Performance Indicators")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)

    with kpi1:
        total_revenue = f_df['Amount'].sum()
        st.metric("Total Revenue", f"£{total_revenue:,.2f}")

    with kpi2:
        # Using the cleaned 'Approved' value
        q_app = len(f_df[f_df['Quality status'] == 'Approved'])
        st.metric("Quality Approved", f"{q_app:,}")

    with kpi3:
        w_done = len(f_df[f_df['Welcome Status'].str.lower() == 'done'])
        st.metric("Welcome Done", f"{w_done:,}")

    with kpi4:
        p_acc = len(f_df[f_df['Payment Status'].str.lower() == 'accepted'])
        st.metric("Payments Accepted", f"{p_acc:,}")

    st.markdown("---")

    # --- MONTHLY TREND ---
    if 'Month' in f_df.columns and not f_df.empty:
        st.subheader("📅 Monthly Revenue Trend")
        monthly_rev = f_df.groupby('Month')['Amount'].sum().reset_index()
        # Handle custom month formatting
        clean_month = monthly_rev['Month'].str.replace('Sept', 'Sep').str.replace('July', 'Jul')
        monthly_rev['DateOrder'] = pd.to_datetime(clean_month, format='%b-%Y', errors='coerce')
        monthly_rev = monthly_rev.dropna(subset=['DateOrder']).sort_values('DateOrder')

        if not monthly_rev.empty:
            fig_trend = px.line(
                monthly_rev, x='Month', y='Amount', 
                markers=True, 
                text=monthly_rev['Amount'].apply(lambda x: f"£{x:,.0f}"),
                labels={"Amount": "Revenue (£)"}
            )
            fig_trend.update_traces(line_color='#00CC96', line_width=3, textposition="top center")
            fig_trend.update_xaxes(type='category', categoryorder='array', categoryarray=monthly_rev['Month'])
            st.plotly_chart(fig_trend, use_container_width=True)

    # --- AGENT PERFORMANCE & QUALITY MIX ---
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.subheader("Revenue by Agent")
        if not f_df.empty:
            rev_chart = f_df.groupby('Agent')['Amount'].sum().sort_values(ascending=False).reset_index()
            fig_rev = px.bar(
                rev_chart, x='Agent', y='Amount', 
                text_auto='.2s', color='Amount',
                color_continuous_scale='Greens'
            )
            st.plotly_chart(fig_rev, use_container_width=True)

    with col_right:
        st.subheader("Quality Mix")
        if not f_df.empty:
            q_mix = f_df['Quality status'].value_counts().reset_index()
            fig_pie = px.pie(q_mix, names='index' if 'index' in q_mix.columns else 'Quality status', values='count' if 'count' in q_mix.columns else 'Quality status', hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)

    # --- CANCELLATION REASON SUMMARY ---
    st.subheader("🚫 Cancellation Reason Summary")
    if not f_df.empty and 'Reason of cancellation' in f_df.columns:
        cancel_df = f_df[f_df['Quality status'] != 'Approved']
        if not cancel_df.empty:
            reason_counts = cancel_df['Reason of cancellation'].value_counts().reset_index()
            reason_counts.columns = ['Reason', 'Count']
            
            fig_reasons = px.bar(
                reason_counts.head(10), 
                y='Reason', x='Count',
                orientation='h',
                text_auto=True,
                color='Count',
                color_continuous_scale='Reds'
            )
            fig_reasons.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_reasons, use_container_width=True)
        else:
            st.write("No cancellations found in current selection.")

    # --- AGENT PERFORMANCE MATRIX ---
    st.subheader("Agent-Wise Status Matrix")
    if not f_df.empty:
        matrix = f_df.groupby('Agent').agg({
            'Amount': 'sum',
            'Quality status': lambda x: (x == 'Approved').sum(),
            'Welcome Status': lambda x: (x.str.lower() == 'done').sum(),
            'Payment Status': lambda x: (x.str.lower() == 'accepted').sum()
        }).rename(columns={
            'Amount': 'Total Revenue (£)',
            'Quality status': 'Approved (Q)',
            'Welcome Status': 'Done (W)',
            'Payment Status': 'Accepted (P)'
        }).sort_values(by='Total Revenue (£)', ascending=False).reset_index()

        st.dataframe(matrix.style.format({"Total Revenue (£)": "£{:,.2f}"}), use_container_width=True, hide_index=True)

    # --- SEARCH ---
    with st.expander("🔍 Search Transaction Details"):
        search_query = st.text_input("Search by Customer Name or Phone Number")
        if search_query:
            search_df = f_df[
                (f_df['Customer Name'].str.contains(search_query, case=False, na=False)) |
                (f_df['Phone No.'].astype(str).str.contains(search_query, na=False))
            ]
            st.dataframe(search_df.style.format({"Amount": "£{:,.2f}"}), use_container_width=True)
        else:
            st.dataframe(f_df.style.format({"Amount": "£{:,.2f}"}), use_container_width=True)

except Exception as e:
    st.error(f"Error: {e}")
