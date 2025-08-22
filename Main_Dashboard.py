import streamlit as st
import pandas as pd
import snowflake.connector
import plotly.express as px
import plotly.graph_objects as go
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

# --- Page Config: Tab Title & Icon -------------------------------------------------------------------------------------
st.set_page_config(
    page_title="Axelar Network Performance",
    page_icon="https://img.cryptorank.io/coins/axelar1663924228506.png",
    layout="wide"
)

# --- Title with Logo ---------------------------------------------------------------------------------------------------
st.markdown(
    """
    <div style="display: flex; align-items: center; gap: 15px;">
        <img src="https://img.cryptorank.io/coins/axelar1663924228506.png" alt="Axelar Logo" style="width:60px; height:60px;">
        <h1 style="margin: 0;">Axelar Network Performance: Annual Report</h1>
    </div>
    """,
    unsafe_allow_html=True
)

# --- Builder Info ---------------------------------------------------------------------------------------------------------
st.markdown(
    """
    <div style="margin-top: 20px; margin-bottom: 20px; font-size: 16px;">
        <div style="display: flex; align-items: center; gap: 10px;">
            <img src="https://pbs.twimg.com/profile_images/1841479747332608000/bindDGZQ_400x400.jpg" style="width:25px; height:25px; border-radius: 50%;">
            <span>Built by: <a href="https://x.com/0xeman_raz" target="_blank">Eman Raz</a></span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# --- Info Box --------------------------------------------------------------------------------------------------------------
st.markdown(
    """
    <div style="background-color: #e5f3fc; padding: 10px; border-radius: 1px; border: 1px solid #e5f3fc;">
        🎉Welcome to the Axelar Performance Dashboard!
        Axelar is a decentralized interoperability network enabling seamless communication between blockchains. This dashboard provides a 
        comprehensive analysis of Axelar's performance metrics, including transaction count, network activity, and key usage trends. 
    </div>
    """,
    unsafe_allow_html=True
)

st.info("⏳On-chain data retrieval may take a few moments. Please wait while the results load.")

# --- Snowflake Connection ----------------------------------------------------------------------------------------
snowflake_secrets = st.secrets["snowflake"]
user = snowflake_secrets["user"]
account = snowflake_secrets["account"]
private_key_str = snowflake_secrets["private_key"]
warehouse = snowflake_secrets.get("warehouse", "")
database = snowflake_secrets.get("database", "")
schema = snowflake_secrets.get("schema", "")

private_key_pem = f"-----BEGIN PRIVATE KEY-----\n{private_key_str}\n-----END PRIVATE KEY-----".encode("utf-8")
private_key = serialization.load_pem_private_key(
    private_key_pem,
    password=None,
    backend=default_backend()
)
private_key_bytes = private_key.private_bytes(
    encoding=serialization.Encoding.DER,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
)

conn = snowflake.connector.connect(
    user=user,
    account=account,
    private_key=private_key_bytes,
    warehouse=warehouse,
    database=database,
    schema=schema
)

# --- Row (1). Snowflake Query with Caching ----------------------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def get_kpis():
    query = """
    with table1 as (with tab1 as (
    select count(distinct tx_id) as "2024 Txns", 
    count(distinct tx_from) as "2024 Users"
    from axelar.core.fact_transactions
    where block_timestamp::date>='2024-01-01' and block_timestamp::date<='2024-12-31'),

    tab2 as (
    select 
    count(distinct tx_id) as "2023 Txns", 
    count(distinct tx_from) as "2023 Users"
    from axelar.core.fact_transactions
    where block_timestamp::date>='2023-01-01' and block_timestamp::date<='2023-12-31')

    select 
    round(((("2024 Txns"-"2023 Txns")/"2023 Txns")*100),2) as "%Txn Change", 
    round(((("2024 Users"-"2023 Users")/"2023 Users")*100),2) as "%User Change"
    from tab1, tab2),
   
    table2 as (with tab1 as (
    select round(avg(fee/pow(10,6)),4) as "2024 Avg",
    round(median(fee/pow(10,6)),4) as "2024 Median"
    from axelar.core.fact_transactions
    where fee_denom='uaxl' and tx_succeeded='TRUE' and
    block_timestamp::date>='2024-01-01' and block_timestamp::date<='2024-12-31'),

    tab2 as (
    select 
    round(avg(fee/pow(10,6)),4) as "2023 Avg",
    round(median(fee/pow(10,6)),4) as "2023 Median"
    from axelar.core.fact_transactions
    where fee_denom='uaxl' and tx_succeeded='TRUE' and
    block_timestamp::date>='2023-01-01' and block_timestamp::date<='2023-12-31')

    select 
    round(((("2024 Avg"-"2023 Avg")/"2023 Avg")*100),2) as "% Avg Change", 
    round(((("2024 Median"-"2023 Median")/"2023 Median")*100),2) as "% Median Change"
    from tab1, tab2)

    select "%Txn Change", "%User Change", "% Avg Change", "% Median Change"
    from table1 , table2
    """
    return pd.read_sql(query, conn)

df_kpis = get_kpis()
txn_change = df_kpis.iloc[0]["%Txn Change"]
user_change = df_kpis.iloc[0]["%User Change"]
avg_fee_change = df_kpis.iloc[0]["% Avg Change"]
median_fee_change = df_kpis.iloc[0]["% Median Change"]

# --- Row (1). KPI Display ----------------------------------------------------------------------------------------------------------
col1, col2, col3, col4 = st.columns(4)

def kpi_card(col, title, value):
    color = "green" if value >= 0 else "red"
    col.markdown(
        f"""
        <div style="background-color: #f9f9f9; padding: 15px; border-radius: 8px; text-align: center;">
            <div style="font-size: 16px; font-weight: bold;">
                {title} <span title="Comparison between 2023 and 2024">(?)</span>
            </div>
            <div style="font-size: 24px; color: {color}; font-weight: bold;">
                {value}%
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

kpi_card(col1, "Transaction Growth", txn_change)
kpi_card(col2, "User Growth", user_change)
kpi_card(col3, "Avg Fee Change", avg_fee_change)
kpi_card(col4, "Median Fee Change", median_fee_change)

# --- Row(2). Transactions & Users Per Year -----------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def get_txn_user_per_year():
    query = """
    select date_trunc('year',block_timestamp) as "Date", 
    count(distinct tx_id) as "Number of Transactions",
    count(distinct tx_from) as "Number of Users"
    from axelar.core.fact_transactions
    group by 1
    order by 1
    """
    return pd.read_sql(query, conn)

df_yearly = get_txn_user_per_year()
df_yearly["Date"] = pd.to_datetime(df_yearly["Date"]).dt.year  

# --- Row(2). Peak Transaction Days --------------------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def get_peak_days():
    query = """
    select block_timestamp::date as "Date", 
    count(distinct tx_id) as "Number of Transactions", 
    count(distinct tx_from) as "Number of Users",
    round(sum(fee)/pow(10,6),1) as "Total Txn Fee"
    from axelar.core.fact_transactions
    group by 1
    order by 2 desc 
    limit 10
    """
    return pd.read_sql(query, conn)

df_peak = get_peak_days()
df_peak.index = df_peak.index + 1  
df_peak["Number of Transactions"] = df_peak["Number of Transactions"].map("{:,}".format)
df_peak["Number of Users"] = df_peak["Number of Users"].map("{:,}".format)
df_peak["Total Txn Fee"] = df_peak["Total Txn Fee"].map("{:,.1f}".format)

# --- Row(2). Layout: Chart + Table -----------------------------------------------------------------------------------------------
col1, col2 = st.columns([2, 1])

with col1:
    fig = go.Figure()

    # Bar for Transactions
    fig.add_trace(go.Bar(
        x=df_yearly["Date"],
        y=df_yearly["Number of Transactions"],
        name="Number of Transactions",
        marker_color="black",
        yaxis="y1"
    ))

    # Line for Users
    fig.add_trace(go.Scatter(
        x=df_yearly["Date"],
        y=df_yearly["Number of Users"],
        name="Number of Users",
        mode="lines+markers",
        marker=dict(color="blue"),
        yaxis="y2"
    ))

    # Layout settings
    fig.update_layout(
        title="Transactions & Users Per Year",
        xaxis=dict(title="Year"),
        yaxis=dict(title="Txns count", side="left"),
        yaxis2=dict(
            title="Address count",
            overlaying="y",
            side="right"
        ),
        legend=dict(x=0.02, y=0.98, bgcolor="rgba(0,0,0,0)"),
        bargap=0.2,
        template="plotly_white",
        height=500
    )

    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.markdown("### Days with peak txn counts")
    st.dataframe(
        df_peak,
        use_container_width=True
    )

# -- Row (3) ----------------------------------------------------------------------------------
# --- Query 1: Total Fees Per Year (AXL + USD) ---------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def get_total_fees_per_year():
    query = """
    SELECT  
        date_trunc('year',block_timestamp_hour) as "Date", 
        ROUND(sum(total_fees_native)) as "Total Fees ($AXL)",
        ROUND(sum(total_fees_USD)) as "Total Fees ($USD)"
    from AXELAR.STATS.EZ_CORE_METRICS_HOURLY
    GROUP BY 1
    ORDER BY 1
    """
    return pd.read_sql(query, conn)

df_fees = get_total_fees_per_year()
df_fees["Date"] = pd.to_datetime(df_fees["Date"]).dt.year

fig_fees = go.Figure()
fig_fees.add_trace(go.Bar(
    x=df_fees["Date"], y=df_fees["Total Fees ($AXL)"],
    name="Total Fees ($AXL)", marker_color="black", yaxis="y1"
))
fig_fees.add_trace(go.Scatter(
    x=df_fees["Date"], y=df_fees["Total Fees ($USD)"],
    name="Total Fees ($USD)", mode="lines+markers",
    marker=dict(color="blue"), yaxis="y2"
))
fig_fees.update_layout(
    title="⛽Total Txn Fee Per Year",
    xaxis=dict(title=" "),
    yaxis=dict(title="$AXL", side="left"),
    yaxis2=dict(title="$USD", overlaying="y", side="right"),
    bargap=0.2, template="plotly_white", height=450
)

# --- Query 2: Avg & Median Fees Per Year -------------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def get_avg_median_fees():
    query = """
    select date_trunc('year',block_timestamp) as "Date", 
        round(avg(fee/pow(10,6)),4) as "Avg",
        round(median(fee/pow(10,6)),4) as "Median"
    from axelar.core.fact_transactions
    where fee_denom='uaxl' and tx_succeeded='true'
    group by 1
    order by 1
    """
    return pd.read_sql(query, conn)

df_avg_med = get_avg_median_fees()
df_avg_med["Date"] = pd.to_datetime(df_avg_med["Date"]).dt.year

fig_avg_med = go.Figure()
fig_avg_med.add_trace(go.Scatter(
    x=df_avg_med["Date"], y=df_avg_med["Avg"], name="Avg",
    mode="lines+markers", marker=dict(color="black"), yaxis="y1"
))
fig_avg_med.add_trace(go.Scatter(
    x=df_avg_med["Date"], y=df_avg_med["Median"], name="Median",
    mode="lines+markers", marker=dict(color="blue"), yaxis="y2"
))
fig_avg_med.update_layout(
    title="📊Avg & Median Txn Fees Per Year",
    xaxis=dict(title=" "),
    yaxis=dict(title="$AXL", side="left"),
    yaxis2=dict(title="$AXL", overlaying="y", side="right"),
    template="plotly_white", height=450
)

# --- Query 3: Axelar Users Per Year (Stacked Bar + Line) ---------------------------------------------------------------
@st.cache_data(ttl=3600)
def get_users_per_year():
    query = """
    with table1 as (
        SELECT date_trunc('year',block_timestamp) as "Date", 
               count(distinct tx_from) as "Total Users"
        FROM axelar.core.fact_transactions
        GROUP BY 1
    ),
    table2 as (
        with tab1 as (
            SELECT tx_from, min(block_timestamp::date) as first_date
            FROM axelar.core.fact_transactions
            GROUP BY 1
        )
        select date_trunc('year',first_date) as "Date", count(distinct tx_from) as "New Users"
        from tab1
        group by 1
    )
    select table1."Date" as "Date", "Total Users", "New Users", 
           "Total Users"-"New Users" as "Active Users"
    from table1 
    left join table2 on table1."Date"=table2."Date"
    order by 1
    """
    return pd.read_sql(query, conn)

df_users = get_users_per_year()
df_users["Date"] = pd.to_datetime(df_users["Date"]).dt.year

fig_users = go.Figure()
# New Users
fig_users.add_trace(go.Bar(
    x=df_users["Date"], y=df_users["New Users"], name="New Users",
    marker_color="blue"
))
# Active Users
fig_users.add_trace(go.Bar(
    x=df_users["Date"], y=df_users["Active Users"], name="Active Users",
    marker_color="indigo"
))
# Total Users (line)
fig_users.add_trace(go.Scatter(
    x=df_users["Date"], y=df_users["Total Users"], name="Total Users",
    mode="lines+markers", marker=dict(color="black")
))
fig_users.update_layout(
    title="👥Axelar Users per Year",
    xaxis=dict(title=" "),
    yaxis=dict(title="Wallet count"),
    barmode="stack",
    template="plotly_white", height=450
)

# --- Display all three charts in one row --------------------------------------------------------------------------------
col1, col2, col3 = st.columns(3)
with col1:
    st.plotly_chart(fig_fees, use_container_width=True)
with col2:
    st.plotly_chart(fig_avg_med, use_container_width=True)
with col3:
    st.plotly_chart(fig_users, use_container_width=True)

# --- Reference and Rebuild Info ---
st.markdown(
    """
    <div style="margin-top: 20px; margin-bottom: 20px; font-size: 16px;">
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
            <img src="https://cdn-icons-png.flaticon.com/512/3178/3178287.png" alt="Reference" style="width:20px; height:20px;">
            <span>Dashboard Reference: <a href="https://flipsidecrypto.xyz/bbash/axelar-network-performance-_xMt-m" target="_blank">https://flipsidecrypto.xyz/bbash/axelar-network-performance-_xMt-m</a></span>
        </div>
        <div style="display: flex; align-items: center; gap: 10px;">
            <img src="https://pbs.twimg.com/profile_images/1856738793325268992/OouKI10c_400x400.jpg" alt="Flipside" style="width:25px; height:25px; border-radius: 50%;">
            <span>Data Powered by: <a href="https://flipsidecrypto.xyz/home/" target="_blank">Flipside</a></span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# --- Links with Logos ---
st.markdown(
    """
    <div style="font-size: 16px;">
        <div style="display: flex; align-items: center; gap: 10px;">
            <img src="https://axelarscan.io/logos/logo.png" alt="Axelar" style="width:20px; height:20px;">
            <a href="https://www.axelar.network/" target="_blank">Axelar Website</a>
        </div>
        <div style="display: flex; align-items: center; gap: 10px;">
            <img src="https://axelarscan.io/logos/logo.png" alt="Axelar" style="width:20px; height:20px;">
            <a href="https://x.com/axelar" target="_blank">Axelar X Account</a>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

