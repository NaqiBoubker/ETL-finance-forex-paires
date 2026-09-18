import json
import logging
import sys
import os
from confluent_kafka import Consumer, KafkaError
import snowflake.connector

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from ingestion.utils.helpers import get_snowflake_config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

TOPIC = "fx_prices"

def get_consumer():
    return Consumer({
        "bootstrap.servers": "kafka:29092",
        "group.id":          "snowflake_sink",
        "auto.offset.reset": "earliest"
    })

def get_snowflake_conn():
    return snowflake.connector.connect(**get_snowflake_config())

def ensure_stream_table(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS RAW.raw_prices_stream (
                symbol    STRING,
                date      DATE,
                open      FLOAT,
                high      FLOAT,
                low       FLOAT,
                close     FLOAT,
                timestamp TIMESTAMP,
                CONSTRAINT uq_stream UNIQUE (symbol, timestamp)
            )
        """)
    log.info("Stream table ready.")

def insert_record(conn, record):
    with conn.cursor() as cur:
        cur.execute("""
            MERGE INTO RAW.raw_prices_stream t
            USING (
                SELECT
                    %s::STRING    AS symbol,
                    %s::DATE      AS date,
                    %s::FLOAT     AS open,
                    %s::FLOAT     AS high,
                    %s::FLOAT     AS low,
                    %s::FLOAT     AS close,
                    %s::TIMESTAMP AS timestamp
            ) s
            ON t.symbol = s.symbol AND t.timestamp = s.timestamp
            WHEN NOT MATCHED THEN
                INSERT (symbol, date, open, high, low, close, timestamp)
                VALUES (s.symbol, s.date, s.open, s.high, s.low, s.close, s.timestamp)
        """, (
            record["symbol"],
            record["date"],
            record["open"],
            record["high"],
            record["low"],
            record["close"],
            record["timestamp"]
        ))
        conn.commit()

def run():
    consumer = get_consumer()
    consumer.subscribe([TOPIC])
    conn = get_snowflake_conn()
    ensure_stream_table(conn)

    log.info(f"Consumer started — listening to: {TOPIC}")

    try:
        while True:
            msg = consumer.poll(timeout=1.0)

            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                log.error(f"Kafka error: {msg.error()}")
                continue

            try:
                record = json.loads(msg.value().decode("utf-8"))
                insert_record(conn, record)
                log.info(f"Inserted: {record['symbol']} @ {record['timestamp']}")
            except Exception as e:
                log.error(f"Failed to insert: {e}")
                continue

    finally:
        consumer.close()
        conn.close()
        log.info("Consumer shut down.")

if __name__ == "__main__":
    run()