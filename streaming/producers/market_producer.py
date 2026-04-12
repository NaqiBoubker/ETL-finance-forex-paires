import yfinance as yf
import json
import time
import logging
from datetime import datetime
from confluent_kafka import Producer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

SYMBOLS  = ["EURUSD=X", "GBPUSD=X", "EURGBP=X", "USDCHF=X", "EURAUD=X"]
TOPIC    = "fx_prices"
INTERVAL = 60  # seconds

def get_producer():
    return Producer({"bootstrap.servers": "localhost:9092"})

def delivery_report(err, msg):
    if err:
        log.error(f"Delivery failed: {err}")
    else:
        log.info(f"Delivered → {msg.topic()} [{msg.partition()}]")

def fetch_latest(symbol):
    df = yf.download(symbol, period="1d", interval="1m", progress=False)
    if df.empty:
        return None

    if hasattr(df.columns, "levels"):
        df.columns = df.columns.get_level_values(0)

    row = df.iloc[-1]
    return {
        "symbol":    symbol.replace("=X", ""),
        "date":      df.index[-1].strftime("%Y-%m-%d"),
        "open":      float(row["Open"]),
        "high":      float(row["High"]),
        "low":       float(row["Low"]),
        "close":     float(row["Close"]),
        "timestamp": datetime.utcnow().isoformat()
    }

def run():
    producer = get_producer()
    log.info(f"Producer started — polling every {INTERVAL}s")

    while True:
        for symbol in SYMBOLS:
            try:
                data = fetch_latest(symbol)
                if data:
                    producer.produce(
                        TOPIC,
                        key=data["symbol"],
                        value=json.dumps(data),
                        callback=delivery_report
                    )
                    log.info(f"Produced: {data['symbol']} close={data['close']}")
            except Exception as e:
                log.error(f"Failed for {symbol}: {e}")
                continue

        producer.flush()
        time.sleep(INTERVAL)

if __name__ == "__main__":
    run()