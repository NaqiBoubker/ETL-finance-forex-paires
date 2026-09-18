FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    yfinance \
    confluent-kafka \
    snowflake-connector-python \
    python-dotenv

COPY . .