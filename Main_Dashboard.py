import streamlit as st
import pandas as pd
import snowflake.connector
import plotly.express as px
import plotly.graph_objects as go

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
        <h1 style="margin: 0;">Axelar Network Performance</h1>
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

# --- Snowflake Connection --------------------------------------------------------------------------------------------------
conn = snowflake.connector.connect(
    user=st.secrets["snowflake"]["user"],
    password=st.secrets["snowflake"]["password"],
    account=st.secrets["snowflake"]["account"],
    warehouse="SNOWFLAKE_LEARNING_WH",
    database="AXELAR",
    schema="PUBLIC"
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
                {title} <span title="Comparison between 2023 and 2024">!</span>
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
