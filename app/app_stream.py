import streamlit as st
import pandas as pd
import snowflake.connector
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

def _hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    return [int(hex_color[i:i+2], 16)/255 for i in (0, 2, 4)]

st.set_page_config(
    page_title="FX Terminal",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── Session state defaults ────────────────────────────────
for key, val in {
    "dark_mode":        True,
    "symbol":           "EURUSD",
    "timeframe":        "1D",
    "strategy":         "MA",
    "show_signal":      True,
    "show_regime":      True,
    "show_rsi":         True,
    "show_sharpe":      True,
    "show_cum_return":  True,
    "show_drawdown":    True,
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ── Theme ─────────────────────────────────────────────────
if st.session_state.dark_mode:
    BG, BG2, BG3 = "#131722", "#1E222D", "#2A2E39"
    TEXT, TEXT2  = "#D1D4DC", "#787B86"
    GRID, BORDER = "rgba(255,255,255,0.06)", "#2A2E39"
    GREEN, RED   = "#26A69A", "#EF5350"
    BLUE, ORANGE = "#2196F3", "#FF9800"
    PURPLE       = "#9C27B0"
    TEAL         = "#00BCD4"
else:
    BG, BG2, BG3 = "#FFFFFF", "#F0F3FA", "#E8EBF0"
    TEXT, TEXT2  = "#131722", "#787B86"
    GRID, BORDER = "rgba(0,0,0,0.06)", "#E0E3EB"
    GREEN, RED   = "#089981", "#F23645"
    BLUE, ORANGE = "#1976D2", "#F57C00"
    PURPLE       = "#7B1FA2"
    TEAL         = "#0097A7"

st.markdown(f"""
<style>
    .stApp {{ background-color: {BG}; }}
    .block-container {{ padding: 0.8rem 1.5rem 1rem; max-width: 100%; }}
    section[data-testid="stSidebar"] {{ display: none; }}
    .metric-box {{
        background: {BG2}; border-radius: 6px;
        padding: 10px 14px; border: 1px solid {BORDER};
        min-width: 110px;
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
    .metric-value.blue  {{ color: {BLUE};  }}
    .badge {{
        display: inline-block; font-family: monospace;
        font-size: 11px; font-weight: 600; padding: 3px 10px; border-radius: 3px;
    }}
    .badge-buy     {{ background: rgba(38,166,154,0.15); color: {GREEN}; }}
    .badge-sell    {{ background: rgba(239,83,80,0.15);  color: {RED};   }}
    .badge-hold    {{ background: rgba(33,150,243,0.15); color: {BLUE};  }}
    .badge-neutral {{ background: rgba(120,123,134,0.15); color: {TEXT2}; }}
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
        FROM ANALYTICS.FACT_SIGNALS ORDER BY DATE
    """, get_conn())

@st.cache_data(ttl=300)
def load_backtest():
    return pd.read_sql("""
        SELECT DATE, SYMBOL, STRATEGY_RETURN, CUMULATIVE_RETURN,
               DRAWDOWN, WIN_FLAG, SHARPE_ANNUALIZED
        FROM ANALYTICS.FACT_BACKTEST ORDER BY DATE
    """, get_conn())

@st.cache_data(ttl=300)
def load_ml_signals():
    return pd.read_sql("""
        SELECT DATE, SYMBOL, REGIME, P_BEARISH, P_NEUTRAL, P_BULLISH, ML_SIGNAL
        FROM ANALYTICS.FACT_ML_SIGNALS ORDER BY DATE
    """, get_conn())

@st.cache_data(ttl=300)
def load_ml_backtest():
    return pd.read_sql("""
        SELECT DATE, SYMBOL, STRATEGY_RETURN, CUMULATIVE_RETURN,
               DRAWDOWN, WIN_FLAG, SHARPE_ANNUALIZED
        FROM ANALYTICS.FACT_ML_BACKTEST ORDER BY DATE
    """, get_conn())

@st.cache_data(ttl=30)
def load_stream_symbol(symbol):
    return pd.read_sql(f"""
        SELECT TIMESTAMP, OPEN, HIGH, LOW, CLOSE
        FROM RAW.raw_prices_stream
        WHERE SYMBOL = '{symbol}'
        ORDER BY TIMESTAMP ASC
    """, get_conn())

@st.cache_data(ttl=30)
def load_stream_latest():
    return pd.read_sql("""
        SELECT SYMBOL, CLOSE, TIMESTAMP
        FROM RAW.raw_prices_stream
        QUALIFY ROW_NUMBER() OVER (PARTITION BY SYMBOL ORDER BY TIMESTAMP DESC) = 1
        ORDER BY SYMBOL
    """, get_conn())


# ── Load data ─────────────────────────────────────────────
signals_df     = load_signals()
backtest_df    = load_backtest()
ml_signals_df  = load_ml_signals()
ml_backtest_df = load_ml_backtest()
PAIRS          = sorted(signals_df["SYMBOL"].unique().tolist())

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
    if st.button("☀️" if st.session_state.dark_mode else "🌙", key="dark_toggle"):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()

st.markdown(
    f'<hr style="border:none;border-top:1px solid {BORDER};margin:6px 0 10px;">',
    unsafe_allow_html=True
)

# ── Strategy + Timeframe selectors ───────────────────────
c_strat, c_tf = st.columns([4, 8])

with c_strat:
    st.markdown(
        f'<div style="font-family:monospace;font-size:10px;color:{TEXT2};'
        f'margin-bottom:6px;letter-spacing:0.06em;">STRATEGY</div>',
        unsafe_allow_html=True
    )
    s1, s2, s3 = st.columns(3)
    with s1:
        if st.button(f"{'→ ' if st.session_state.strategy == 'MA' else ''}MA", key="strat_ma"):
            st.session_state.strategy = "MA"
            st.rerun()
    with s2:
        if st.button(f"{'→ ' if st.session_state.strategy == 'HMM' else ''}HMM", key="strat_hmm"):
            st.session_state.strategy = "HMM"
            st.rerun()
    with s3:
        if st.button(f"{'→ ' if st.session_state.strategy == 'NONE' else ''}OFF", key="strat_none"):
            st.session_state.strategy = "NONE"
            st.rerun()

with c_tf:
    st.markdown(
        f'<div style="font-family:monospace;font-size:10px;color:{TEXT2};'
        f'margin-bottom:6px;letter-spacing:0.06em;">TIMEFRAME</div>',
        unsafe_allow_html=True
    )
    t1, t2, _ = st.columns([1, 1, 8])
    with t1:
        if st.button(f"{'→ ' if st.session_state.timeframe == '1D' else ''}1D", key="tf_1d"):
            st.session_state.timeframe = "1D"
            st.rerun()
    with t2:
        if st.button(f"{'→ ' if st.session_state.timeframe == '1M' else ''}1M", key="tf_1m"):
            st.session_state.timeframe = "1M"
            st.rerun()

st.markdown(
    f'<hr style="border:none;border-top:1px solid {BORDER};margin:6px 0 10px;">',
    unsafe_allow_html=True
)

# ── Metric toggles ────────────────────────────────────────
st.markdown(
    f'<div style="font-family:monospace;font-size:10px;color:{TEXT2};'
    f'margin-bottom:6px;letter-spacing:0.06em;">TOGGLE METRICS</div>',
    unsafe_allow_html=True
)

tg = st.columns([1, 1, 1, 1, 1, 1, 4])
toggles = [
    ("tog_sig",    "show_signal",     "Signal"),
    ("tog_regime", "show_regime",     "Regime"),
    ("tog_rsi",    "show_rsi",        "RSI"),
    ("tog_sharpe", "show_sharpe",     "Sharpe"),
    ("tog_cum",    "show_cum_return", "Return"),
    ("tog_dd",     "show_drawdown",   "Drawdown"),
]
for i, (key, state, label) in enumerate(toggles):
    with tg[i]:
        active = st.session_state[state]
        if st.button(f"{label} {'✓' if active else '○'}", key=key):
            st.session_state[state] = not active
            st.rerun()

# ── Filter data ───────────────────────────────────────────
symbol    = st.session_state.symbol
timeframe = st.session_state.timeframe
strategy  = st.session_state.strategy

sig        = signals_df[signals_df["SYMBOL"] == symbol].copy()
ml         = ml_signals_df[ml_signals_df["SYMBOL"] == symbol].copy()
latest_sig = sig.iloc[-1]

# ── Strategy data ─────────────────────────────────────────
if strategy == "MA":
    bt          = backtest_df[backtest_df["SYMBOL"] == symbol].copy()
    latest_bt   = bt.iloc[-1] if not bt.empty else None
    signal_val  = str(latest_sig["TRADING_SIGNAL"])
    badge_cls   = "badge-buy" if "BUY" in signal_val else ("badge-sell" if "SELL" in signal_val else "badge-neutral")
    regime_val  = "—"
    p_bull, p_bear = 0, 0
    chart_color = GREEN
    strat_label = "MA CROSSOVER STRATEGY"
    strat_color = GREEN

elif strategy == "HMM":
    bt          = ml_backtest_df[ml_backtest_df["SYMBOL"] == symbol].copy()
    latest_bt   = bt.iloc[-1] if not bt.empty else None
    latest_ml   = ml.iloc[-1] if not ml.empty else None
    signal_val  = str(latest_ml["ML_SIGNAL"]) if latest_ml is not None else "N/A"
    badge_cls   = "badge-buy" if signal_val == "BUY" else ("badge-sell" if signal_val == "SELL" else "badge-hold")
    regime_val  = str(latest_ml["REGIME"])    if latest_ml is not None else "N/A"
    p_bull      = float(latest_ml["P_BULLISH"]) * 100 if latest_ml is not None else 0
    p_bear      = float(latest_ml["P_BEARISH"]) * 100 if latest_ml is not None else 0
    chart_color = TEAL
    strat_label = "HMM MARKOV STRATEGY"
    strat_color = TEAL

else:
    bt          = None
    latest_bt   = None
    signal_val  = "—"
    badge_cls   = "badge-neutral"
    regime_val  = "—"
    p_bull, p_bear = 0, 0
    chart_color = BLUE
    strat_label = "PRICE CHART ONLY"
    strat_color = TEXT2

sharpe    = float(latest_bt["SHARPE_ANNUALIZED"]) if latest_bt is not None else 0
cum       = float(latest_bt["CUMULATIVE_RETURN"]) * 100 if latest_bt is not None else 0
dd        = float(latest_bt["DRAWDOWN"]) * 100 if latest_bt is not None else 0
rsi_val   = float(latest_sig["RSI_14"]) if latest_sig["RSI_14"] else 0
close_val = float(latest_sig["CLOSE"])

# ── Strategy label ────────────────────────────────────────
st.markdown(
    f'<div style="font-family:monospace;font-size:12px;color:{strat_color};'
    f'margin-bottom:10px;letter-spacing:0.08em;">● {strat_label} — {symbol}</div>',
    unsafe_allow_html=True
)

# ── Metrics bar ───────────────────────────────────────────
metrics_html = '<div style="display:flex;gap:10px;margin-bottom:14px;flex-wrap:wrap;">'

if st.session_state.show_signal:
    metrics_html += f"""
    <div class="metric-box">
        <div class="metric-label">{'MA' if strategy == 'MA' else 'HMM' if strategy == 'HMM' else ''} Signal</div>
        <div class="metric-value"><span class="badge {badge_cls}">{signal_val}</span></div>
    </div>
    <div class="metric-box">
        <div class="metric-label">Last Close</div>
        <div class="metric-value">{close_val:.4f}</div>
    </div>"""

if st.session_state.show_regime and strategy == "HMM":
    metrics_html += f"""
    <div class="metric-box">
        <div class="metric-label">Regime</div>
        <div class="metric-value" style="font-size:13px;">{regime_val}<br>
        <span style="font-size:11px;color:{TEXT2};">Bull:{p_bull:.0f}% Bear:{p_bear:.0f}%</span></div>
    </div>"""

if st.session_state.show_rsi:
    rsi_cls = "red" if rsi_val > 70 else ("green" if rsi_val < 30 else "")
    metrics_html += f"""
    <div class="metric-box">
        <div class="metric-label">RSI 14</div>
        <div class="metric-value {rsi_cls}">{rsi_val:.1f}</div>
    </div>"""

if st.session_state.show_sharpe and strategy != "NONE":
    metrics_html += f"""
    <div class="metric-box">
        <div class="metric-label">Sharpe (20d)</div>
        <div class="metric-value {'green' if sharpe >= 0 else 'red'}">{sharpe:.2f}</div>
    </div>"""

if st.session_state.show_cum_return and strategy != "NONE":
    metrics_html += f"""
    <div class="metric-box">
        <div class="metric-label">Cum Return</div>
        <div class="metric-value {'green' if cum >= 0 else 'red'}">{cum:+.2f}%</div>
    </div>"""

if st.session_state.show_drawdown and strategy != "NONE":
    metrics_html += f"""
    <div class="metric-box">
        <div class="metric-label">Max Drawdown</div>
        <div class="metric-value red">{dd:.2f}%</div>
    </div>"""

metrics_html += '</div>'
st.markdown(metrics_html, unsafe_allow_html=True)

# ── Axis style ────────────────────────────────────────────
axis_style = dict(
    showgrid=True, gridcolor=GRID, gridwidth=0.5,
    zeroline=False,
    tickfont=dict(family="monospace", size=10, color=TEXT2),
    linecolor=BORDER, showline=True
)

# ── 1D Chart ──────────────────────────────────────────────
if timeframe == "1D":
    if strategy == "NONE":
        fig = make_subplots(rows=1, cols=1)
    else:
        fig = make_subplots(
            rows=3, cols=1, shared_xaxes=True,
            row_heights=[0.55, 0.23, 0.22],
            vertical_spacing=0.02
        )

    # Price
    fig.add_trace(go.Scatter(
        x=sig["DATE"], y=sig["CLOSE"], name="Close",
        line=dict(color=chart_color, width=1.5),
        hovertemplate="%{y:.4f}<extra></extra>"
    ), row=1, col=1)

    if strategy == "MA":
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

    elif strategy == "HMM":
        if not ml.empty:
            ml_merged = ml.merge(sig[["DATE", "CLOSE"]], on="DATE", how="left")
            price_max = sig["CLOSE"].max()
            price_min = sig["CLOSE"].min()

            for regime, color in [("BULLISH", GREEN), ("BEARISH", RED), ("NEUTRAL", ORANGE)]:
                mask = ml_merged["REGIME"] == regime
                if mask.any():
                    rd  = ml_merged[mask]["DATE"]
                    rgb = _hex_to_rgb(color)
                    fig.add_trace(go.Scatter(
                        x=pd.concat([rd, rd[::-1]]),
                        y=[price_max] * len(rd) + [price_min] * len(rd),
                        fill="toself",
                        fillcolor=f"rgba({int(rgb[0]*255)},{int(rgb[1]*255)},{int(rgb[2]*255)},0.07)",
                        line=dict(width=0),
                        name=regime, showlegend=True, hoverinfo="skip"
                    ), row=1, col=1)

            ml_buy  = ml_merged[ml_merged["ML_SIGNAL"] == "BUY"]
            ml_sell = ml_merged[ml_merged["ML_SIGNAL"] == "SELL"]

            fig.add_trace(go.Scatter(
                x=ml_buy["DATE"], y=ml_buy["CLOSE"],
                mode="markers", name="HMM Buy",
                marker=dict(symbol="triangle-up", size=9, color=TEAL,
                            line=dict(color=BG, width=1)),
                hovertemplate="HMM BUY: %{y:.4f}<extra></extra>"
            ), row=1, col=1)

            fig.add_trace(go.Scatter(
                x=ml_sell["DATE"], y=ml_sell["CLOSE"],
                mode="markers", name="HMM Sell",
                marker=dict(symbol="triangle-down", size=9, color=RED,
                            line=dict(color=BG, width=1)),
                hovertemplate="HMM SELL: %{y:.4f}<extra></extra>"
            ), row=1, col=1)

    if strategy != "NONE":
        # RSI panel
        fig.add_trace(go.Scatter(
            x=sig["DATE"], y=sig["RSI_14"], name="RSI 14",
            line=dict(color=PURPLE, width=1.5),
            hovertemplate="RSI: %{y:.1f}<extra></extra>"
        ), row=2, col=1)

        fig.add_hrect(y0=70, y1=100, fillcolor=RED,   opacity=0.05, line_width=0, row=2, col=1)
        fig.add_hrect(y0=0,  y1=30,  fillcolor=GREEN, opacity=0.05, line_width=0, row=2, col=1)
        fig.add_hline(y=70, line_dash="dot", line_color=RED,   line_width=0.8, row=2, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color=GREEN, line_width=0.8, row=2, col=1)

        # Cum return panel
        cum_color = chart_color if bt["CUMULATIVE_RETURN"].iloc[-1] >= 0 else RED
        fill_map  = {GREEN: "rgba(38,166,154,0.08)", TEAL: "rgba(0,188,212,0.08)"}
        fill_col  = fill_map.get(cum_color, "rgba(239,83,80,0.08)")

        fig.add_trace(go.Scatter(
            x=bt["DATE"], y=bt["CUMULATIVE_RETURN"] * 100,
            name="Cum Return", line=dict(color=cum_color, width=1.5),
            fill="tozeroy", fillcolor=fill_col,
            hovertemplate="Return: %{y:.2f}%<extra></extra>"
        ), row=3, col=1)

    layout_args = dict(
        height=600 if strategy != "NONE" else 450,
        margin=dict(l=10, r=70, t=10, b=10),
        plot_bgcolor=BG, paper_bgcolor=BG,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0,
            font=dict(family="monospace", size=11, color=TEXT2),
            bgcolor="rgba(0,0,0,0)", borderwidth=0
        ),
        hovermode="x unified",
        hoverlabel=dict(bgcolor=BG3, font_size=11, font_family="monospace", font_color=TEXT),
        yaxis=dict(**axis_style, side="right", autorange=True, fixedrange=False),
        dragmode="pan"
    )

    if strategy != "NONE":
        layout_args.update({
            "xaxis":  dict(**axis_style, showticklabels=False),
            "xaxis2": dict(**axis_style, showticklabels=False),
            "xaxis3": dict(**axis_style),
            "yaxis2": dict(**axis_style, side="right", range=[0, 100], fixedrange=False),
            "yaxis3": dict(**axis_style, side="right", ticksuffix="%", autorange=True, fixedrange=False),
        })
    else:
        layout_args["xaxis"] = dict(**axis_style)

    fig.update_layout(**layout_args)

# ── 1M Chart ──────────────────────────────────────────────
else:
    stream_df = load_stream_symbol(symbol)
    fig = make_subplots(rows=1, cols=1)

    if stream_df.empty:
        st.warning("No streaming data yet for this symbol.")
    else:
        stream_df["is_flat"] = (
            (stream_df["OPEN"] == stream_df["CLOSE"]) &
            (stream_df["HIGH"] == stream_df["LOW"])
        )
        flat_pct = stream_df["is_flat"].mean()

        if flat_pct > 0.8:
            st.info("🕐 Market closed — showing last known prices. Live candles appear when market opens.")
            fig.add_trace(go.Scatter(
                x=stream_df["TIMESTAMP"],
                y=stream_df["CLOSE"],
                name="Close",
                line=dict(color=GREEN, width=1.5),
                hovertemplate="%{x}<br>Close: %{y:.4f}<extra></extra>"
            ), row=1, col=1)
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
            ), row=1, col=1)

        latest_price = float(stream_df["CLOSE"].iloc[-1])
        fig.add_hline(
            y=latest_price,
            line_dash="dot", line_color=TEXT2, line_width=0.8,
            annotation_text=f"  {latest_price:.4f}",
            annotation_position="right",
            annotation_font=dict(family="monospace", size=10, color=TEXT2)
        )

        # X range — last 3 hours
        t_max = pd.to_datetime(stream_df["TIMESTAMP"].max())
        t_min = t_max - timedelta(hours=3)

        fig.update_xaxes(
            range=[t_min, t_max + timedelta(minutes=10)],
            rangeslider=dict(visible=False),
            **axis_style
        )

        # Y axis — fully flexible, auto-scales to visible candles
        fig.update_yaxes(
            autorange=True,
            fixedrange=False,
            **axis_style,
            side="right"
        )

    st.markdown(
        f'<div style="font-family:monospace;font-size:11px;color:{TEXT2};margin-bottom:6px;">'
        f'<span class="live-dot"></span>LIVE — {symbol} — 1 MIN — Kafka → Snowflake</div>',
        unsafe_allow_html=True
    )

    fig.update_layout(
        height=500,
        margin=dict(l=10, r=80, t=10, b=10),
        plot_bgcolor=BG,
        paper_bgcolor=BG,
        hovermode="x unified",
        hoverlabel=dict(bgcolor=BG3, font_size=11, font_family="monospace", font_color=TEXT),
        yaxis=dict(**axis_style, side="right", autorange=True, fixedrange=False),
        dragmode="pan"
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
        f'<span style="font-family:monospace;font-size:11px;color:{TEXT2};">'
        f'<span class="live-dot"></span>LIVE PRICES — raw_prices_stream</span>',
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