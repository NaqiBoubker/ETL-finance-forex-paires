import streamlit as st
import pandas as pd
import snowflake.connector

import os
from dotenv import load_dotenv

load_dotenv()

def get_snowflake_config():
    return {
        "user": os.getenv("SNOWFLAKE_USER"),
        "password": os.getenv("SNOWFLAKE_PASSWORD"),
        "account": os.getenv("SNOWFLAKE_ACCOUNT"),
        "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
        "database": os.getenv("SNOWFLAKE_DATABASE"),
        "schema": os.getenv("SNOWFLAKE_SCHEMA"),
    }

st.title("FX Trading Dashboard")

conn = snowflake.connector.connect(**get_snowflake_config())

query = "SELECT * FROM ANALYTICS.fact_backtest"
df = pd.read_sql(query, conn)

symbol = st.selectbox("Select pair", df['SYMBOL'].unique())

filtered = df[df['SYMBOL'] == symbol]

st.line_chart(filtered.set_index('DATE')['CUMULATIVE_RETURN'])