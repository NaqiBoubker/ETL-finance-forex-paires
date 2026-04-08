import yfinance as yf
import snowflake.connector
from datetime import datetime, timedelta
import logging
import time
from ..utils.helpers import get_snowflake_config

# ── Logging ──────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

SYMBOLS = [
    "EURUSD=X",
    "GBPUSD=X",
    "EURGBP=X",
    "USDCHF=X",
    "EURAUD=X",
]

START_DATE = datetime(2023, 1, 1).date()


# ── Connection ───────────────────────────────────────────
def get_connection():
    return snowflake.connector.connect(**get_snowflake_config())


# ── Table ────────────────────────────────────────────────
def ensure_table(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS RAW.raw_prices (
                date    DATE,
                open    FLOAT,
                high    FLOAT,
                low     FLOAT,
                close   FLOAT,
                symbol  STRING,
                CONSTRAINT unique_price UNIQUE (date, symbol)
            )
        """)
    log.info("Table ready.")


# ── Incremental logic ────────────────────────────────────
def get_last_date(conn, symbol):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT MAX(date) FROM RAW.raw_prices WHERE symbol = %s",
            (symbol,)
        )
        result = cur.fetchone()[0]

    return (result - timedelta(days=1)) if result else START_DATE


# ── Fetch data ───────────────────────────────────────────
def fetch_data(symbol, start_date, retries=3):
    end_date = datetime.today().strftime('%Y-%m-%d')
    start_str = start_date.strftime('%Y-%m-%d')
    clean_symbol = symbol.replace("=X", "")

    for attempt in range(1, retries + 1):
        try:
            log.info(f"{symbol} → fetching (attempt {attempt})")

            df = yf.download(
                symbol,
                start=start_str,
                end=end_date,
                progress=False,
                auto_adjust=False,
                threads=False
            )

            if df.empty:
                log.warning(f"No data for {symbol}")
                return None

            # 🔥 FIX: flatten MultiIndex columns
            if hasattr(df.columns, "levels"):
                df.columns = df.columns.get_level_values(0)

            # Validate columns
            required = {'Open', 'High', 'Low', 'Close'}
            if not required.issubset(df.columns):
                log.warning(f"Invalid format for {symbol}: {df.columns}")
                return None

            df.reset_index(inplace=True)
            df = df[['Date', 'Open', 'High', 'Low', 'Close']].copy()

            df['symbol'] = clean_symbol
            df['Date'] = df['Date'].dt.date

            df.dropna(inplace=True)

            log.info(f"{clean_symbol} → {len(df)} rows fetched")
            return df

        except Exception as e:
            log.warning(f"{symbol} failed attempt {attempt}: {e}")
            time.sleep(3)

    return None


# ── Insert data ──────────────────────────────────────────
def insert_data(conn, df, symbol):
    tmp = f"RAW.tmp_{symbol.lower()}_{int(time.time())}"
    rows = list(df.itertuples(index=False, name=None))

    with conn.cursor() as cur:
        cur.execute(f"""
            CREATE TEMPORARY TABLE {tmp} (
                date DATE,
                open FLOAT,
                high FLOAT,
                low FLOAT,
                close FLOAT,
                symbol STRING
            )
        """)

        cur.executemany(f"""
            INSERT INTO {tmp} VALUES (%s,%s,%s,%s,%s,%s)
        """, rows)

        cur.execute(f"""
            MERGE INTO RAW.raw_prices t
            USING {tmp} s
            ON t.date = s.date AND t.symbol = s.symbol
            WHEN NOT MATCHED THEN INSERT VALUES
            (s.date, s.open, s.high, s.low, s.close, s.symbol)
        """)

        conn.commit()
        log.info(f"{symbol} merged ({len(rows)} rows)")

        cur.execute(f"DROP TABLE IF EXISTS {tmp}")


def safe_insert(conn, df, symbol):
    try:
        insert_data(conn, df, symbol)
    except Exception as e:
        log.warning(f"Insert failed → retry: {e}")
        time.sleep(3)
        insert_data(conn, df, symbol)


# ── Main ─────────────────────────────────────────────────
if __name__ == "__main__":
    conn = get_connection()

    try:
        ensure_table(conn)

        for symbol in SYMBOLS:
            clean = symbol.replace("=X", "")

            try:
                start = get_last_date(conn, clean)
                log.info(f"{clean} start: {start}")

                df = fetch_data(symbol, start)

                if df is not None:
                    safe_insert(conn, df, clean)

            except Exception as e:
                log.error(f"{clean} failed: {e}")
                continue

    finally:
        conn.close()
        log.info("✅ Incremental FX ingestion complete.")