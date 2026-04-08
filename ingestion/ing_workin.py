import yfinance as yf
import snowflake.connector
from .utils.helpers import get_snowflake_config


import yfinance as yf


symbols = [
    "EURUSD=X",
    "GBPUSD=X",
    "EURGBP=X",
    "USDCHF=X",
    "EURAUD=X",
    
]

def fetch_data(symbol):
    print(f"Fetching data for {symbol}...")
    df = yf.download(symbol, start="2023-01-01", end="2023-12-31")
    
    # Reset index to move Date from index to a column
    df.reset_index(inplace=True)
    
    # Keep only the columns we need
    df = df[['Date', 'Open', 'High', 'Low', 'Close']]
    
    # Add symbol column
    df['symbol'] = symbol.replace("=X", "") 
    
    # Convert Date column to Python datetime (Snowflake compatible)
    df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
    
    return df
def get_connection():
    config = get_snowflake_config()
    return snowflake.connector.connect(**config)
    
def create_table(conn):
    create_table_query = """
    CREATE OR REPLACE TABLE RAW.raw_prices (
        date DATE,
        open FLOAT,
        high FLOAT,
        low FLOAT,
        close FLOAT,
        symbol STRING
    )
    """
    with conn.cursor() as cur:
        cur.execute(create_table_query)
    print("Table RAW.raw_prices created successfully.")


def insert_data(conn, df):
    """
    Inserts a pandas DataFrame into the RAW.raw_prices table in Snowflake.
    """
    insert_query = """
        INSERT INTO RAW.raw_prices (date, open, high, low, close, symbol)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    
    # Convert DataFrame to list of tuples
    data_to_insert = list(df.itertuples(index=False, name=None))
    
    # Use executemany to insert all rows at once
    with conn.cursor() as cursor:
        cursor.executemany(insert_query, data_to_insert)
    
    print(f"{len(data_to_insert)} rows inserted successfully.")
    print("Data inserted successfully.")


if __name__ == "__main__":
    conn = get_connection()


    print("Creating table...")
    create_table(conn)

   
    for symbol in symbols:
        print(f"Fetching {symbol}...")
        df = fetch_data(symbol)

        print(f"Inserting {symbol}...")
        insert_data(conn, df)

    conn.close()

    print("✅ All FX data loaded into Snowflake!")


