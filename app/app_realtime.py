import streamlit as st
import pandas as pd
import snowflake.connector
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="FX Terminal",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── Session state defaults ────────────────────────────────
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = True
if "symbol" not in st.session_state:
    st.session_state.symbol = "EURUSD"
if "timeframe" not in st.session_state:
    st.session_state.timeframe = "1D"

# ── Theme ─────────────────────────────────────────────────
if st.session_state.dark_mode:
    BG, BG2, BG3   = "#131722", "#1E222D", "#2A2E39"
    TEXT, TEXT2    = "#D1D4DC", "#787B86"
    GRID, BORDER   = "rgba(255,255,255,0.06)", "#2A2E39"
    GREEN, RED     = "#26A69A", "#EF5350"
    BLUE, ORANGE   = "#2196F3", "#FF9800"
    PURPLE         = "#9C27B0"
else:
    BG, BG2, BG3   = "#FFFFFF", "#F0F3FA", "#E8EBF0"
    TEXT, TEXT2    = "#131722", "#787B86"
    GRID, BORDER   = "rgba(0,0,0,0.06)", "#E0E3EB"
    GREEN, RED     = "#089981", "#F23645"
    BLUE, ORANGE   = "#1976D2", "#F57C00"
    PURPLE         = "#7B1FA2"

st.markdown(f"""
<style>
    .stApp {{ background-color: {BG}; }}
    .block-container {{ padding: 0.8rem 1.5rem 1rem; max-width: 100%; }}
    section[data-testid="stSidebar"] {{ display: none; }}
    .metric-bar {{
        display: grid; grid-template-columns: repeat(5, 1fr);
        gap: 10px; margin-bottom: 14px;
    }}
    .metric-box {{
        background: {BG2}; border-radius: 6px;
        padding: 10px 14px; border: 1px solid {BORDER};
    }}
    .metric-label {{
        font-family: monospace; font-size: 10px; color: {TEXT2};
        letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 4px;
    }}
    .metric-value {{
        font-family: monospace; font-size: 20px;
        font-weight: 600; color: {TEXT};
    }}
    .metric-value.green {{ color: {GREEN}; }}
    .metric-value.red   {{ color: {RED};   }}
    .badge {{
        display: inline-block; font-family: monospace;
        font-size: 11px; font-weight: 600; padding: 3px 10px; border-radius: 3px;
    }}
    .badge-buy     {{ background: rgba(38,166,154,0.15); color: {GREEN}; }}
    .badge-sell    {{ background: rgba(239,83,80,0.15);  color: {RED};   }}
    .badge-neutral {{ background: rgba(120,123,134,0.15); color: {TEXT2}; }}
    .tf-bar {{
        display: flex; gap: 4px; align-items: center; margin-bottom: 10px;
    }}
    .tf-label {{
        font-family: monospace; font-size: 10px; color: {TEXT2};
        letter-spacing: 0.06em; margin-right: 8px;
    }}
    .live-dot {{
        display: inline-block; width: 7px; height: 7px;
        border-radius: 50%; background: {GREEN};
        margin-right: 6px; animation: pulse 1.5s infinite;
    }}
    @keyframes pulse {{
        0%   {{ opacity: 1; }}
        50%  {{ opacity: 0.3; }}
        100% {{ opacity: 1; }}
    }}
    .live-table {{ width: 100%; border-collapse: collapse; }}
    .live-table th {{
        font-family: monospace; font-size: 10px; color: {TEXT2};
        text-transform: uppercase; letter-spacing: 0.06em;
        padding: 6px 12px; border-bottom: 1px solid {BORDER}; text-align: left;
    }}
    .live-table td {{
        font-family: monospace; font-size: 13px; color: {TEXT};
        padding: 7px 12px; border-bottom: 1px solid {BORDER};
    }}
    .live-table tr:last-child td {{ border-bottom: none; }}
    .live-price {{ color: {GREEN}; font-weight: 600; }}
    .stButton > button {{
        font-family: monospace !important; font-size: 12px !important;
        padding: 4px 14px !important; border-radius: 4px !important;
        border: 1px solid {BORDER} !important;
        background: {BG2} !important; color: {TEXT2} !important;
    }}
    .stButton > button:hover {{
        border-color: {GREEN} !important; color: {TEXT} !important;
    }}
    #MainMenu, footer, header {{ visibility: hidden; }}
    .stDeployButton {{ display: none; }}
</style>
""", unsafe_allow_html=True)


# ── Snowflake ─────────────────────────────────────────────
@st.cache_resource
def get_conn():
    return snowflake.connector.connect(
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema="ANALYTICS"
    )

@st.cache_data(ttl=300)
def load_signals():
    return pd.read_sql("""
        SELECT DATE, SYMBOL, CLOSE, RETURN,
               MA_5D, MA_20D, RSI_14,
               TREND_SIGNAL, RSI_SIGNAL, TRADING_SIGNAL
        FROM ANALYTICS.FACT_SIGNALS
        ORDER BY DATE
    """, get_conn())

@st.cache_data(ttl=300)
def load_backtest():
    return pd.read_sql("""
        SELECT DATE, SYMBOL,
               STRATEGY_RETURN, CUMULATIVE_RETURN,
               DRAWDOWN, WIN_FLAG, SHARPE_ANNUALIZED
        FROM ANALYTICS.FACT_BACKTEST
        ORDER BY DATE
    """, get_conn())

@st.cache_data(ttl=60)
def load_stream_symbol(symbol):
    """Load last 200 1-minute bars for a symbol from Kafka stream."""
    return pd.read_sql(f"""
        SELECT
            TIMESTAMP,
            OPEN, HIGH, LOW, CLOSE
        FROM RAW.raw_prices_stream
        WHERE SYMBOL = '{symbol}'
        ORDER BY TIMESTAMP DESC
        LIMIT 200
    """, get_conn())

@st.cache_data(ttl=60)
def load_stream_latest():
    """Load latest price per symbol for the live table."""
    return pd.read_sql("""
        SELECT SYMBOL, CLOSE, TIMESTAMP
        FROM RAW.raw_prices_stream
        QUALIFY ROW_NUMBER() OVER (PARTITION BY SYMBOL ORDER BY TIMESTAMP DESC) = 1
        ORDER BY SYMBOL
    """, get_conn())


# ── Data ──────────────────────────────────────────────────
signals_df  = load_signals()
backtest_df = load_backtest()
PAIRS       = sorted(signals_df["SYMBOL"].unique().tolist())

# ── Top bar ───────────────────────────────────────────────
c_logo, c_pairs, c_mode = st.columns([1, 5, 1])

with c_logo:
    st.markdown(
        f'<div style="font-family:monospace;font-size:15px;font-weight:600;'
        f'color:{TEXT};letter-spacing:0.1em;padding-top:6px;">FX / TERMINAL</div>',
        unsafe_allow_html=True
    )

with c_pairs:
    cols = st.columns(len(PAIRS))
    for i, pair in enumerate(PAIRS):
        with cols[i]:
            if st.button(pair, key=f"btn_{pair}"):
                st.session_state.symbol = pair
                st.rerun()

with c_mode:
    label = "☀️" if st.session_state.dark_mode else "🌙"
    if st.button(label, key="dark_toggle"):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()

st.markdown(
    f'<hr style="border:none;border-top:1px solid {BORDER};margin:6px 0 10px;">',
    unsafe_allow_html=True
)

# ── Timeframe selector ────────────────────────────────────
TIMEFRAMES = ["1D", "1M"]
tf_cols = st.columns([3, 1, 1, 6])

with tf_cols[0]:
    st.markdown(
        f'<div style="font-family:monospace;font-size:11px;color:{TEXT2};'
        f'letter-spacing:0.06em;padding-top:8px;">TIMEFRAME</div>',
        unsafe_allow_html=True
    )

for i, tf in enumerate(TIMEFRAMES):
    with tf_cols[i + 1]:
        active = st.session_state.timeframe == tf
        label  = f"{'→ ' if active else ''}{tf}"
        if st.button(label, key=f"tf_{tf}"):
            st.session_state.timeframe = tf
            st.rerun()

symbol    = st.session_state.symbol
timeframe = st.session_state.timeframe

# ── Load correct data for timeframe ──────────────────────
sig = signals_df[signals_df["SYMBOL"] == symbol].copy()
bt  = backtest_df[backtest_df["SYMBOL"] == symbol].copy()
latest_sig = sig.iloc[-1]
latest_bt  = bt.iloc[-1]

# ── Metrics ───────────────────────────────────────────────
signal_val = str(latest_sig["TRADING_SIGNAL"])
badge_cls  = "badge-buy" if "BUY" in signal_val else ("badge-sell" if "SELL" in signal_val else "badge-neutral")
sharpe     = float(latest_bt["SHARPE_ANNUALIZED"])
dd         = float(latest_bt["DRAWDOWN"]) * 100
cum        = float(latest_bt["CUMULATIVE_RETURN"]) * 100
close_val  = float(latest_sig["CLOSE"])
rsi_val    = float(latest_sig["RSI_14"]) if latest_sig["RSI_14"] else 0

st.markdown(f"""
<div class="metric-bar">
  <div class="metric-box">
    <div class="metric-label">Signal (1D)</div>
    <div class="metric-value"><span class="badge {badge_cls}">{signal_val}</span></div>
  </div>
  <div class="metric-box">
    <div class="metric-label">Last Close</div>
    <div class="metric-value">{close_val:.4f}</div>
  </div>
  <div class="metric-box">
    <div class="metric-label">RSI 14</div>
    <div class="metric-value {'red' if rsi_val > 70 else 'green' if rsi_val < 30 else ''}">{rsi_val:.1f}</div>
  </div>
  <div class="metric-box">
    <div class="metric-label">Sharpe (20d)</div>
    <div class="metric-value {'green' if sharpe >= 0 else 'red'}">{sharpe:.2f}</div>
  </div>
  <div class="metric-box">
    <div class="metric-label">Cum Return</div>
    <div class="metric-value {'green' if cum >= 0 else 'red'}">{cum:+.2f}%</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Chart ─────────────────────────────────────────────────
axis_style = dict(
    showgrid=True, gridcolor=GRID, gridwidth=0.5,
    zeroline=False,
    tickfont=dict(family="monospace", size=10, color=TEXT2),
    linecolor=BORDER, showline=True
)

if timeframe == "1D":
    # ── Daily chart — line + MAs + signals + RSI + cum return ──
    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True,
        row_heights=[0.55, 0.23, 0.22],
        vertical_spacing=0.02
    )

    fig.add_trace(go.Scatter(
        x=sig["DATE"], y=sig["CLOSE"], name="Close",
        line=dict(color=GREEN, width=1.5),
        hovertemplate="%{y:.4f}<extra></extra>"
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=sig["DATE"], y=sig["MA_5D"], name="MA5",
        line=dict(color=ORANGE, width=1, dash="dot"),
        hovertemplate="MA5: %{y:.4f}<extra></extra>"
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=sig["DATE"], y=sig["MA_20D"], name="MA20",
        line=dict(color=BLUE, width=1, dash="dash"),
        hovertemplate="MA20: %{y:.4f}<extra></extra>"
    ), row=1, col=1)

    buy_sig  = sig[sig["TRADING_SIGNAL"].isin(["BUY", "STRONG_BUY"])]
    sell_sig = sig[sig["TRADING_SIGNAL"].isin(["SELL", "STRONG_SELL"])]

    fig.add_trace(go.Scatter(
        x=buy_sig["DATE"], y=buy_sig["CLOSE"],
        mode="markers", name="Buy",
        marker=dict(symbol="triangle-up", size=9, color=GREEN),
        hovertemplate="BUY: %{y:.4f}<extra></extra>"
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=sell_sig["DATE"], y=sell_sig["CLOSE"],
        mode="markers", name="Sell",
        marker=dict(symbol="triangle-down", size=9, color=RED),
        hovertemplate="SELL: %{y:.4f}<extra></extra>"
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=sig["DATE"], y=sig["RSI_14"], name="RSI 14",
        line=dict(color=PURPLE, width=1.5),
        hovertemplate="RSI: %{y:.1f}<extra></extra>"
    ), row=2, col=1)

    fig.add_hrect(y0=70, y1=100, fillcolor=RED,   opacity=0.05, line_width=0, row=2, col=1)
    fig.add_hrect(y0=0,  y1=30,  fillcolor=GREEN, opacity=0.05, line_width=0, row=2, col=1)
    fig.add_hline(y=70, line_dash="dot", line_color=RED,   line_width=0.8, row=2, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color=GREEN, line_width=0.8, row=2, col=1)

    cum_color = GREEN if bt["CUMULATIVE_RETURN"].iloc[-1] >= 0 else RED
    fill_col  = "rgba(38,166,154,0.08)" if cum_color == GREEN else "rgba(239,83,80,0.08)"
    fig.add_trace(go.Scatter(
        x=bt["DATE"], y=bt["CUMULATIVE_RETURN"] * 100,
        name="Cum Return", line=dict(color=cum_color, width=1.5),
        fill="tozeroy", fillcolor=fill_col,
        hovertemplate="Return: %{y:.2f}%<extra></extra>"
    ), row=3, col=1)

    fig.update_layout(
        height=600, margin=dict(l=10, r=70, t=10, b=10),
        plot_bgcolor=BG, paper_bgcolor=BG,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0,
            font=dict(family="monospace", size=11, color=TEXT2),
            bgcolor="rgba(0,0,0,0)", borderwidth=0
        ),
        hovermode="x unified",
        hoverlabel=dict(bgcolor=BG3, font_size=11, font_family="monospace", font_color=TEXT),
        xaxis=dict(**axis_style, showticklabels=False),
        xaxis2=dict(**axis_style, showticklabels=False),
        xaxis3=dict(**axis_style),
        yaxis=dict(**axis_style, side="right"),
        yaxis2=dict(**axis_style, side="right", range=[0, 100]),
        yaxis3=dict(**axis_style, side="right", ticksuffix="%"),
        dragmode="pan"
    )

else:
    # ── 1M chart — candlestick from Kafka stream ──────────
    stream_df = load_stream_symbol(symbol)
    stream_df = stream_df.sort_values("TIMESTAMP")

    fig = make_subplots(
        rows=1, cols=1,
        vertical_spacing=0.02
    )

    if stream_df.empty:
        st.warning("No streaming data yet for this symbol.")
    else:
        fig.add_trace(go.Candlestick(
            x=stream_df["TIMESTAMP"],
            open=stream_df["OPEN"],
            high=stream_df["HIGH"],
            low=stream_df["LOW"],
            close=stream_df["CLOSE"],
            name="1M",
            increasing=dict(line=dict(color=GREEN, width=1), fillcolor=GREEN),
            decreasing=dict(line=dict(color=RED,   width=1), fillcolor=RED),
            hovertext=stream_df["TIMESTAMP"].astype(str),
        ), row=1, col=1)

        # Live price line
        latest_price = float(stream_df["CLOSE"].iloc[-1])
        fig.add_hline(
            y=latest_price,
            line_dash="dot", line_color=TEXT2, line_width=0.8,
            annotation_text=f"  {latest_price:.4f}",
            annotation_position="right",
            annotation_font=dict(family="monospace", size=10, color=TEXT2)
        )

    fig.update_layout(
        height=500, margin=dict(l=10, r=80, t=10, b=10),
        plot_bgcolor=BG, paper_bgcolor=BG,
        hovermode="x unified",
        hoverlabel=dict(bgcolor=BG3, font_size=11, font_family="monospace", font_color=TEXT),
        xaxis=dict(**axis_style, rangeslider=dict(visible=False)),
        yaxis=dict(**axis_style, side="right"),
        dragmode="pan"
    )

    # Live indicator
    st.markdown(
        f'<div style="font-family:monospace;font-size:11px;color:{TEXT2};margin-bottom:6px;">'
        f'<span class="live-dot"></span>LIVE — {symbol} — 1 MIN — Kafka → Snowflake'
        f'</div>',
        unsafe_allow_html=True
    )

st.plotly_chart(fig, use_container_width=True, config={
    "scrollZoom": True,
    "displayModeBar": True,
    "modeBarButtonsToRemove": ["autoScale2d", "lasso2d", "select2d"],
    "displaylogo": False
})

# ── Live stream table ─────────────────────────────────────
c1, c2 = st.columns([6, 1])
with c1:
    st.markdown(
        f'<span style="font-family:monospace;font-size:11px;color:{TEXT2};'
        f'letter-spacing:0.08em;"><span class="live-dot"></span>'
        f'LIVE PRICES — raw_prices_stream</span>',
        unsafe_allow_html=True
    )
with c2:
    if st.button("↻ Refresh", key="refresh"):
        st.cache_data.clear()
        st.rerun()

try:
    latest_df = load_stream_latest()
    if not latest_df.empty:
        rows_html = "".join([
            f"<tr><td>{r['SYMBOL']}</td>"
            f"<td class='live-price'>{float(r['CLOSE']):.4f}</td>"
            f"<td>{str(r['TIMESTAMP'])[:19]}</td></tr>"
            for _, r in latest_df.iterrows()
        ])
        st.markdown(f"""
        <table class="live-table">
            <thead><tr><th>Symbol</th><th>Price</th><th>Last Update</th></tr></thead>
            <tbody>{rows_html}</tbody>
        </table>""", unsafe_allow_html=True)
except Exception as e:
    st.error(f"Stream error: {e}")