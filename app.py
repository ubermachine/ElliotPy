import streamlit as st
import pandas as pd
import numpy as np
import datetime
import subprocess
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from backend.data_manager import DataManager
from backend.wave_engine import DailyElliottWaveEngine, WaveNode, Pivot

# Set up Streamlit Page Configuration
st.set_page_config(
    page_title="Elliott Wave Charting Engine",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Premium CSS Injection
st.markdown("""
<style>
    /* Main Background & Fonts */
    .stApp {
        background-color: #0B0F19;
        color: #E2E8F0;
        font-family: 'Outfit', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Headers & Text colors */
    h1, h2, h3 {
        color: #F8FAFC !important;
        font-weight: 700;
        letter-spacing: -0.02em;
    }
    
    /* Glassmorphism sidebar & containers */
    section[data-testid="stSidebar"] {
        background-color: #111827 !important;
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    /* Styled metric cards */
    div.metric-card {
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 12px;
        transition: all 0.3s ease;
    }
    
    div.metric-card:hover {
        background: rgba(255, 255, 255, 0.04);
        border-color: rgba(0, 240, 255, 0.2);
    }
    
    /* Tabs Custom Styling */
    button[data-baseweb="tab"] {
        color: #94A3B8 !important;
        font-weight: 600 !important;
        background-color: transparent !important;
    }
    button[aria-selected="true"] {
        color: #00F0FF !important;
        border-bottom-color: #00F0FF !important;
    }
    
    /* Tables */
    table {
        background-color: #111827;
        border-collapse: collapse;
        width: 100%;
        border-radius: 8px;
        overflow: hidden;
    }
    
    th {
        background-color: #1F2937 !important;
        color: #00F0FF !important;
        font-weight: 600 !important;
        padding: 12px !important;
        text-align: left !important;
    }
    
    td {
        padding: 10px 12px !important;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05) !important;
    }
</style>
""", unsafe_allow_html=True)

# Helper to keep a drawn-pivot registry to avoid duplicate label stacking
_drawn_pivots: set = set()

# Helper function to recursively draw waves
def add_wave_traces(fig: go.Figure, wave: WaveNode, use_log: bool, degree_depth: int, show_confidence: bool, _drawn: set = None):
    if _drawn is None:
        _drawn = set()
    degree_map = {'Cycle': 1, 'Primary': 2, 'Intermediate': 3, 'Minor': 4, 'Minuette': 5}
    if degree_map.get(wave.degree, 6) > degree_depth:
        return
    # Styling map for degrees
    if show_confidence:
        if wave.score >= 8.0:
            color = "#00FF00"  # High
        elif wave.score >= 5.0:
            color = "#FFC837"  # Med
        else:
            color = "#FF003C"  # Low
        width = 2.0
        dash = 'solid'
    else:
        if wave.degree == "Cycle":
            color = "#FF4A6B"
            width = 3.5
            dash = 'solid'
        elif wave.degree == "Primary":
            color = "#00F0FF"
            width = 3.0
            dash = 'solid'
        elif wave.degree == "Intermediate":
            color = "#FFC837"
            width = 2.0
            dash = 'dash'
        elif wave.degree == "Minor":
            color = "#A0AEC0"
            width = 2.0
            dash = 'dot'
        elif wave.degree == "Minute":
            color = "#F472B6"
            width = 1.5
            dash = 'dashdot'
        elif wave.degree == "Minuette":
            color = "#9CA3AF"
            width = 1.0
            dash = 'longdash'
        else:
            color = "#E2E8F0"
            width = 1.0
            dash = 'longdashdot'
        
    x_coords = [wave.start_pivot.time, wave.end_pivot.time]
    y_coords = [wave.start_pivot.price, wave.end_pivot.price]
    
    # Draw segment (Wave Line) - Hiden as requested
    # fig.add_trace(go.Scattergl(
    #     x=x_coords,
    #     y=y_coords,
    #     mode='lines',
    #     line=dict(color=color, width=width, dash=dash),
    #     name=f"{wave.degree} {wave.label}",
    #     showlegend=False,
    #     hoverinfo='skip'
    # ), row=1, col=1)
    
    # Draw end pivot marker and text label
    is_high = wave.end_pivot.type == "HIGH"
    label_text = wave.label
    if getattr(wave, 'is_truncated', False):
        label_text += " (Truncated)"
    
    # Visual hierarchy: fade out lower degree noise
    opacity = 1.0
    if not show_confidence:
        if wave.degree in ["Cycle", "Primary"]:
            opacity = 1.0
        elif wave.degree == "Intermediate":
            opacity = 0.85
        elif wave.degree == "Minor":
            opacity = 0.7
        elif wave.degree == "Minute":
            opacity = 0.5
        else:
            opacity = 0.35
            
    # Label deduplication: skip if this pivot has already been drawn at this degree
    pivot_key = (wave.end_pivot.time, wave.degree)
    if pivot_key not in _drawn:
        _drawn.add(pivot_key)
        # Text positioning with background
        fib_hint = ""
        if wave.fib_levels:
            nearest_fib = min(wave.fib_levels.values(), key=lambda x: abs(x - wave.end_pivot.price))
            fib_ratio = min(wave.fib_levels.keys(), key=lambda k: abs(wave.fib_levels[k] - wave.end_pivot.price))
            fib_hint = f"<br>Near Fib {fib_ratio}"
        score_hint = f"<br>Score: {wave.score:.1f}" if wave.score > 0 else ""
        fig.add_trace(go.Scattergl(
            x=[wave.end_pivot.time],
            y=[wave.end_pivot.price],
            mode='markers+text',
            text=[label_text],
            textposition="top center" if is_high else "bottom center",
            textfont=dict(
                color="#FFFFFF" if wave.degree in ["Cycle", "Primary"] else color,
                size=14 if wave.degree in ["Cycle", "Primary"] else 12,
                family="'Inter', sans-serif",
                weight="bold"
            ),
            marker=dict(
                color=color,
                size=8 if wave.degree in ["Cycle", "Primary"] else 5,
                symbol="circle",
                line=dict(color="#0B0F19", width=1.5)
            ),
            opacity=opacity,
            name=f"Pivot {wave.label}",
            showlegend=False,
            hoverinfo='text',
            hovertext=f"<b>Wave {wave.label}</b><br>Degree: {wave.degree}<br>Price: {wave.end_pivot.price:,.2f}<br>Date: {wave.end_pivot.time}{score_hint}{fib_hint}"
        ), row=1, col=1)
    
    # Draw start pivot label for the very first wave in sequence
    if wave.label in ["[1]", "(1)", "1", "I", "i"]:
        start_key = (wave.start_pivot.time, wave.degree + "_start")
        if start_key not in _drawn:
            _drawn.add(start_key)
            start_offset = 0.985 if is_high else 1.015
            fig.add_trace(go.Scattergl(
                x=[wave.start_pivot.time],
                y=[wave.start_pivot.price * start_offset],
                mode='text+markers',
                text=["0"],
                textposition="bottom center" if is_high else "top center",
                textfont=dict(color=color, size=11),
                marker=dict(color=color, size=4, symbol="square"),
                opacity=opacity,
                showlegend=False,
                hoverinfo='skip'
            ), row=1, col=1)

    # Recurse children sub-waves
    for sw in wave.sub_waves:
        add_wave_traces(fig, sw, use_log, degree_depth, show_confidence, _drawn)

def find_last_motive_sequence(waves: list[WaveNode]) -> list[WaveNode]:
    """Finds the most recent 5-wave motive sequence in a list of waves."""
    n = len(waves)
    for i in range(n - 4, -1, -1):
        sub = waves[i:i+5]
        labels = [w.label for w in sub]
        if any(labels == l for l in [
            ["[1]", "[2]", "[3]", "[4]", "[5]"],
            ["(1)", "(2)", "(3)", "(4)", "(5)"],
            ["1", "2", "3", "4", "5"],
            ["{1}", "{2}", "{3}", "{4}", "{5}"],
            ["i", "ii", "iii", "iv", "v"]
        ]):
            return sub
    return []

def find_last_wave_block(waves: list[WaveNode]) -> list[WaveNode]:
    """Gets the most recent cohesive wave structure (either 5 motive waves or 3 corrective waves)."""
    if not waves:
        return []
    last_label = waves[-1].label
    if last_label in ["[5]", "(5)", "5", "{5}", "v"]:
        return waves[-5:] if len(waves) >= 5 else waves
    elif last_label in ["[C]", "(C)", "C", "{C}", "c"]:
        return waves[-3:] if len(waves) >= 3 else waves
    else:
        degree = waves[-1].degree
        degree_waves = [w for w in waves if w.degree == degree]
        if len(degree_waves) >= 5:
            if degree_waves[-1].label in ["[5]", "(5)", "5", "{5}", "v"] or degree_waves[-5].label in ["[1]", "(1)", "1", "{1}", "i"]:
                return degree_waves[-5:]
        if len(degree_waves) >= 3:
            return degree_waves[-3:]
        return degree_waves

def add_w5_projection(fig: go.Figure, waves: list, use_log: bool):
    """Draws W5 expectation zones using three Fib projections from W4 end."""
    if len(waves) < 4:
        return
    w1, w2, w3, w4 = waves[0], waves[1], waves[2], waves[3]

    v0 = w1.start_pivot.log_price if use_log else w1.start_pivot.price
    v3 = w3.end_pivot.log_price if use_log else w3.end_pivot.price
    v4 = w4.end_pivot.log_price if use_log else w4.end_pivot.price

    range_13 = abs(v3 - v0)
    is_up = v3 > v0

    targets_log = [
        ("0.618", v4 + (0.618 * range_13 if is_up else -0.618 * range_13), "rgba(0,240,255,0.10)"),
        ("1.000", v4 + (1.000 * range_13 if is_up else -1.000 * range_13), "rgba(0,240,255,0.07)"),
        ("1.618", v4 + (1.618 * range_13 if is_up else -1.618 * range_13), "rgba(0,240,255,0.04)"),
    ]

    start_date = w4.end_pivot.time
    end_date = start_date + datetime.timedelta(days=60)

    for i in range(len(targets_log) - 1):
        label, lo_log, fill = targets_log[i]
        hi_log = targets_log[i + 1][1]
        lo = np.exp(lo_log) if use_log else lo_log
        hi = np.exp(hi_log) if use_log else hi_log
        fig.add_shape(
            type="rect",
            x0=start_date, y0=min(lo, hi),
            x1=end_date, y1=max(lo, hi),
            fillcolor=fill,
            line=dict(color="rgba(0, 240, 255, 0.3)", width=1, dash="dash"),
            row=1, col=1
        )
        # Label the extension levels
        fig.add_annotation(
            x=end_date, y=max(lo, hi) if is_up else min(lo, hi),
            text=f"W5 {targets_log[i+1][0]}",
            showarrow=False,
            font=dict(color="rgba(0,240,255,0.7)", size=9),
            xanchor="left",
            row=1, col=1
        )

def add_parallel_channel(fig: go.Figure, waves: list[WaveNode], use_log: bool):
    """Draws a parallel trendline channel based on Pivot 1, 2, 3 projected from Pivot 4."""
    if len(waves) < 4:
        return
    w1, w2, w3, w4 = waves[0], waves[1], waves[2], waves[3]
    
    p1 = w1.end_pivot
    p2 = w2.end_pivot
    p3 = w3.end_pivot
    p4 = w4.end_pivot
    
    # Calculate slope in log/linear space between Pivot 1 and Pivot 3
    t_span = p3.index - p1.index
    if t_span <= 0:
        return
        
    y1 = p1.log_price if use_log else p1.price
    y3 = p3.log_price if use_log else p3.price
    slope = (y3 - y1) / t_span
    
    # Base line values
    y2 = p2.log_price if use_log else p2.price
    
    # Project channel lines out to the future index
    max_idx = p4.index + 90
    dates = []
    y_channel_top = []
    y_channel_bottom = []
    
    # Use index-to-date mapping
    df = st.session_state.df
    for idx in range(p2.index, min(max_idx, len(df))):
        dates.append(df['Date'].iloc[idx])
        
        # Parallel lines
        log_val_top = y1 + slope * (idx - p1.index)
        log_val_bottom = y2 + slope * (idx - p2.index)
        
        if use_log:
            y_channel_top.append(np.exp(log_val_top))
            y_channel_bottom.append(np.exp(log_val_bottom))
        else:
            y_channel_top.append(log_val_top)
            y_channel_bottom.append(log_val_bottom)
            
    fig.add_trace(go.Scattergl(
        x=dates, y=y_channel_top,
        mode='lines',
        line=dict(color="rgba(156, 163, 175, 0.25)", width=1.5, dash="dash"),
        name="Channel Top",
        showlegend=False,
        hoverinfo='skip'
    ), row=1, col=1)
    
    fig.add_trace(go.Scattergl(
        x=dates, y=y_channel_bottom,
        mode='lines',
        line=dict(color="rgba(156, 163, 175, 0.25)", width=1.5, dash="dash"),
        name="Channel Bottom",
        showlegend=False,
        hoverinfo='skip'
    ), row=1, col=1)


# App Header Setup
st.title("🌊 Elliott Wave Charting Engine")
st.subheader("Daily Timeframe Volatility-Adaptive Structural Analyzer")

# Sidebar Configuration
st.sidebar.header("📊 Controls & Inputs")

preset_options = {
    "Silver Futures (SI=F)": "SI=F",
    "Gold Futures (GC=F)": "GC=F",
    "S&P 500 Index (^SPX)": "^SPX",
    "Bitcoin (BTC-USD)": "BTC-USD",
    "Apple Inc. (AAPL)": "AAPL"
}

preset_choice = st.sidebar.selectbox("Select Asset Preset:", list(preset_options.keys()))
custom_symbol = st.sidebar.text_input("Or enter custom symbol (Yahoo Ticker):", "")

active_symbol = custom_symbol.strip() if custom_symbol.strip() else preset_options[preset_choice]

atr_multiplier = st.sidebar.slider(
    "Adaptive ATR Volatility Multiplier (T1 Sensitivity):",
    min_value=0.5, max_value=3.0, value=1.5, step=0.1,
    help="Higher values increase the Zig-Zag threshold, filtering out smaller price fluctuations to find larger degrees."
)

# Functions to fetch data from DuckDB cache
def get_historical_data(symbol: str) -> tuple[pd.DataFrame, bool]:
    dm = DataManager()
    return dm.fetch_data(symbol, force_refresh=False)

def get_incremental_sync(symbol: str) -> tuple[pd.DataFrame, bool]:
    dm = DataManager()
    return dm.sync_incremental(symbol)

# The wave engine math is extremely fast (<50ms), so we run it fresh to avoid stale cache issues
def get_wave_analysis(df: pd.DataFrame, use_log: bool, atr_multiplier: float):
    engine = DailyElliottWaveEngine(df, use_log_scale=use_log)
    primary_count, alternates = engine.run_analysis(min_move_mult=atr_multiplier)
    return primary_count, alternates, engine

def get_pivots(df: pd.DataFrame, use_log: bool, atr_multiplier: float):
    engine = DailyElliottWaveEngine(df, use_log_scale=use_log)
    pivots_t1 = engine.run_adaptive_zigzag(atr_multiplier)
    pivots_t2 = engine.run_adaptive_zigzag(atr_multiplier * 0.5)
    return pivots_t1, pivots_t2

# Check for Incremental Resync or GitHub Push trigger in sidebar
sync_clicked = st.sidebar.button("🔄 Incremental Resync", help="Downloads and appends new daily bars since the last cached date.")
push_clicked = st.sidebar.button("📤 Push to GitHub", help="Pushes the current cached database to GitHub.")

if sync_clicked:
    st.cache_data.clear()  # Clear cache to force reload
    try:
        df, auto_log = get_incremental_sync(active_symbol)
        st.sidebar.success("Data synced successfully!")
    except Exception as e:
        st.sidebar.error(f"Sync error: {e}")
        df, auto_log = get_historical_data(active_symbol)
elif push_clicked:
    df, auto_log = get_historical_data(active_symbol)
    if "GITHUB_TOKEN" not in st.secrets or "GITHUB_REPO" not in st.secrets:
        st.sidebar.warning("GitHub Sync skipped: Missing GITHUB_TOKEN or GITHUB_REPO in Streamlit secrets.")
    else:
        st.sidebar.info("Pushing to GitHub...")
        try:
            token = st.secrets["GITHUB_TOKEN"]
            repo = st.secrets["GITHUB_REPO"]
            subprocess.run(["git", "config", "--global", "user.email", "bot@elliotpy.local"], check=False)
            subprocess.run(["git", "config", "--global", "user.name", "ElliotPy Bot"], check=False)
            subprocess.run(["git", "add", "data_cache.db", "data/*.parquet"], check=True)
            
            res = subprocess.run(["git", "commit", "-m", f"Auto-sync {active_symbol} data"], capture_output=True, text=True)
            if "nothing to commit" in res.stdout:
                st.sidebar.info("No new data to push.")
            else:
                remote_url = f"https://x-access-token:{token}@github.com/{repo}.git"
                subprocess.run(["git", "remote", "set-url", "origin", remote_url], check=True)
                subprocess.run(["git", "push", "origin", "main"], check=True)
                st.sidebar.success("Successfully pushed database to GitHub!")
        except subprocess.CalledProcessError as e:
            st.sidebar.error(f"GitHub Sync Failed: {e.stderr or e.output}")
        except Exception as e:
            st.sidebar.error(f"Push error: {e}")
else:
    df, auto_log = get_historical_data(active_symbol)

st.session_state.df = df

# Log scale toggle
use_log = st.sidebar.toggle("Use Logarithmic Scale", value=auto_log)

st.sidebar.markdown("---")
st.sidebar.subheader("👁️ Display Options")
degree_depth = st.sidebar.slider("Degree Depth (1-5):", min_value=1, max_value=5, value=3, help="1=Cycle/Primary only, 5=All sub-waves")
show_confidence = st.sidebar.toggle("Confidence Heatmap", value=False, help="Color code waves based on rule confidence score")
show_major_swings = st.sidebar.checkbox("Show Major Swings (T1)", value=False)
show_minor_swings = st.sidebar.checkbox("Show Minor Swings (T2)", value=False)
zoom_bars = st.sidebar.slider(
    "Default Visible Daily Bars (Zoom):",
    min_value=100, max_value=min(1250, len(df)), value=min(500, len(df)), step=50,
    help="Restricts the default visible range of the chart to show the most recent days. Pan or drag to scroll back in time."
)

st.sidebar.markdown("---")
st.sidebar.subheader("💰 Risk & Position Sizing")
account_equity = st.sidebar.number_input("Account Equity ($):", min_value=1000, value=100000, step=1000)
risk_pct = st.sidebar.slider("Risk Per Trade (%):", min_value=0.1, max_value=5.0, value=1.0, step=0.1)


# Execute Elliott Wave Calculation using cached function
primary_count, alternates, engine = get_wave_analysis(df, use_log, atr_multiplier)
df = engine.df  # Ensure computed indicators (RSI, MACD, etc.) are available in df

# Check active count validity
is_invalidated = False
invalidation_msg = "✅ Primary Count Active & Valid"
invalidation_price = None

if primary_count:
    # Check invalidation of W1 start (Pivot 0 of the motive sequence)
    # Get active motif sequence invalidation price (we placed it on W2/W4)
    for wave in primary_count:
        if wave.invalidation_price is not None:
            invalidation_price = wave.invalidation_price
            break
            
    if invalidation_price is not None:
        last_close = df['Close'].iloc[-1]
        is_uptrend = primary_count[0].end_pivot.price > primary_count[0].start_pivot.price
        
        if is_uptrend and last_close <= invalidation_price:
            is_invalidated = True
        elif not is_uptrend and last_close >= invalidation_price:
            is_invalidated = True

tab_ew, tab_inst = st.tabs(["🌊 Elliott Wave Engine", "🏦 Institutional Flow & Profile"])

with tab_ew:
    if is_invalidated:
        st.error(f"🚨 PRIMARY COUNT INVALIDATED: Latest close ({df['Close'].iloc[-1]:,.2f}) breached the invalidation level ({invalidation_price:,.2f})!")
    else:
        st.success(f"📈 {invalidation_msg} | Current Price: {df['Close'].iloc[-1]:,.2f}")

    # Build Interactive Plotly Chart
    fig = make_subplots(
        rows=3, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.03, 
        row_heights=[0.60, 0.20, 0.20]
    )



    # Calculate full swings
    pivots_t1, pivots_t2 = get_pivots(df, use_log, atr_multiplier)

    # Overlay Minor Swings (T2)
    if show_minor_swings:
        fig.add_trace(go.Scattergl(
            x=[p.time for p in pivots_t2],
            y=[p.price for p in pivots_t2],
            mode='lines',
            line=dict(color='rgba(251, 191, 36, 0.25)', width=1, dash='dash'),
            name='Minor Swings (T2)',
            showlegend=True
        ), row=1, col=1)
    
    # Overlay Major Swings (T1)
    if show_major_swings:
        fig.add_trace(go.Scattergl(
            x=[p.time for p in pivots_t1],
            y=[p.price for p in pivots_t1],
            mode='lines+markers',
            line=dict(color='rgba(156, 163, 175, 0.4)', width=1.5),
            marker=dict(color='rgba(156, 163, 175, 0.6)', size=4),
            name='Major Swings (T1)',
            showlegend=True
        ), row=1, col=1)

    # Display Selection for Counts
    count_options = ["Primary Count (Highest Score)"]
    for i, alt in enumerate(alternates):
        count_options.append(f"Alternate Count #{i+1}")
    
    selected_count_name = st.radio("Select Count to Overlay:", count_options, horizontal=True)

    active_waves = primary_count
    if selected_count_name == "Primary Count (Highest Score)" and is_invalidated and alternates:
        st.warning("⚠️ Automatically falling back to Alternate Count #1 due to Primary Count invalidation.")
        active_waves = alternates[0]
    elif selected_count_name != "Primary Count (Highest Score)":
        alt_idx = int(selected_count_name.split("#")[-1]) - 1
        active_waves = alternates[alt_idx]

    # Determine trend color for price line based on last detected wave direction
    _price_line_color = "#ffffff"
    if active_waves:
        last_w = active_waves[-1]
        _is_bull = last_w.end_pivot.price > last_w.start_pivot.price
        _price_line_color = "#00F0FF" if _is_bull else "#FF4A6B"

    # Add Line Chart with area fill
    fig.add_trace(go.Scattergl(
        x=df['Date'],
        y=df['Close'],
        mode='lines',
        name="Price",
        line=dict(color=_price_line_color, width=1.5),
        fill='tozeroy',
        fillcolor='rgba(0,240,255,0.04)'
    ), row=1, col=1)
    


    # Render Wave Nodes recursively
    for wave in active_waves:
        add_wave_traces(fig, wave, use_log, degree_depth, show_confidence)
    
    # Project parallel channels and Wave 5 targets for the most recent impulse sequence found
    recent_motive_seq = find_last_motive_sequence(active_waves)
    if recent_motive_seq:
        add_w5_projection(fig, recent_motive_seq, use_log)
        add_parallel_channel(fig, recent_motive_seq, use_log)
    
    # Add Invalidation Level Trace
    if invalidation_price is not None:
        fig.add_hline(
            y=invalidation_price,
            line_color="#FF003C",
            line_dash="dash",
            line_width=1.5,
            annotation_text="Invalidation Line",
            annotation_position="bottom right",
            annotation_font=dict(color="#FF003C", size=10),
            row=1, col=1
        )

    # Plot Targets for both Primary and Alternate Scenarios
    if primary_count:
        last_block = find_last_wave_block(primary_count)
        rec = engine.get_trade_recommendation(last_block)
        if rec["target"] is not None:
            fig.add_hline(
                y=rec["target"],
                line_color="#10B981",
                line_dash="dot",
                line_width=2,
                annotation_text="🎯 Primary Target",
                annotation_position="top right",
                annotation_font=dict(color="#10B981", size=11, family="Outfit"),
                row=1, col=1
            )
            # Dummy trace for legend
            fig.add_trace(go.Scattergl(
                x=[None], y=[None], mode='lines',
                line=dict(color="#10B981", dash="dot", width=2),
                name="🎯 Primary Target",
                showlegend=True
            ), row=1, col=1)

    if alternates:
        last_block_alt = find_last_wave_block(alternates[0])
        rec_alt = engine.get_trade_recommendation(last_block_alt)
        if rec_alt["target"] is not None and rec_alt["target"] != rec.get("target"):
            fig.add_hline(
                y=rec_alt["target"],
                line_color="#F59E0B",
                line_dash="dot",
                line_width=2,
                annotation_text="🔀 Alternate Target",
                annotation_position="bottom right",
                annotation_font=dict(color="#F59E0B", size=11, family="Outfit"),
                row=1, col=1
            )
            # Dummy trace for legend
            fig.add_trace(go.Scattergl(
                x=[None], y=[None], mode='lines',
                line=dict(color="#F59E0B", dash="dot", width=2),
                name="🔀 Alternate Target",
                showlegend=True
            ), row=1, col=1)

    
    # Add RSI Trace
    if 'RSI' in df.columns:
        fig.add_trace(go.Scattergl(
            x=df['Date'], y=df['RSI'], 
            name='RSI (14)', 
            line=dict(color='#00F0FF', width=1.5),
            showlegend=False
        ), row=2, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="rgba(255,255,255,0.3)", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="rgba(255,255,255,0.3)", row=2, col=1)
    
        # Check for divergence to highlight
        if recent_motive_seq and len(recent_motive_seq) >= 5:
            w3 = recent_motive_seq[2]
            w5 = recent_motive_seq[4]
            if not pd.isna(df['RSI'].iloc[w3.end_pivot.index]) and not pd.isna(df['RSI'].iloc[w5.end_pivot.index]):
                fig.add_trace(go.Scattergl(
                    x=[w3.end_pivot.time, w5.end_pivot.time],
                    y=[df['RSI'].iloc[w3.end_pivot.index], df['RSI'].iloc[w5.end_pivot.index]],
                    mode='lines', line=dict(color='yellow', width=2, dash='dot'),
                    showlegend=False
                ), row=2, col=1)

    # Add MACD Trace
    if 'MACD' in df.columns:
        # MACD Line
        fig.add_trace(go.Scattergl(
            x=df['Date'], y=df['MACD'], 
            name='MACD', 
            line=dict(color='#3B82F6', width=1.5),
            showlegend=False
        ), row=3, col=1)
        # Signal Line
        fig.add_trace(go.Scattergl(
            x=df['Date'], y=df['MACD_Signal'], 
            name='Signal', 
            line=dict(color='#F59E0B', width=1.2, dash='dot'),
            showlegend=False
        ), row=3, col=1)
        # Histogram
        hist_colors = ['#10B981' if val >= 0 else '#EF4444' for val in df['MACD_Hist']]
        fig.add_trace(go.Bar(
            x=df['Date'], y=df['MACD_Hist'], 
            name='Histogram', 
            marker_color=hist_colors,
            showlegend=False
        ), row=3, col=1)

    # Calculate visible Y-range for the default zoom view (last zoom_bars)
    visible_df = df.tail(zoom_bars)
    y_min = float(visible_df['Low'].min())
    y_max = float(visible_df['High'].max())


    # Add a 5% padding
    y_min_padded = y_min * 0.95
    y_max_padded = y_max * 1.05


    # Plotly expects base-10 log values for range limits when axis type is 'log'
    if use_log:
        y_range = [np.log10(y_min_padded), np.log10(y_max_padded)]
    else:
        y_range = [y_min_padded, y_max_padded]

    # Layout Config
    fig.update_layout(
        height=850,
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis=dict(
            gridcolor='rgba(255, 255, 255, 0.1)',
            gridwidth=1,
            griddash='dot',
            type='date',
            range=[df['Date'].iloc[-zoom_bars].strftime("%Y-%m-%d"), (df['Date'].iloc[-1] + datetime.timedelta(days=45)).strftime("%Y-%m-%d")],
            title="",
            showline=False,
            zeroline=False
        ),
        yaxis=dict(
            type='log' if use_log else 'linear',
            gridcolor='rgba(255, 255, 255, 0.1)',
            gridwidth=1,
            griddash='dot',
            side='right',
            range=y_range,
            title="",
            showline=False,
            zeroline=False
        ),
        yaxis2=dict(
            gridcolor='rgba(255, 255, 255, 0.1)',
            gridwidth=1,
            griddash='dot',
            side='right',
            range=[10, 90],
            title="RSI (14)"
        ),
        yaxis3=dict(
            gridcolor='rgba(255, 255, 255, 0.1)',
            gridwidth=1,
            griddash='dot',
            side='right',
            title="MACD"
        ),
        plot_bgcolor='#0F172A',
        paper_bgcolor='#0B0F19',
        hovermode='x unified',
        font=dict(family="'Outfit', 'Inter', sans-serif", color="#E2E8F0")
    )

    # Explicitly disable rangeslider (Plotly Candlesticks override layout defaults)
    fig.update_xaxes(rangeslider_visible=False)

    st.plotly_chart(fig, use_container_width=True, theme=None)

    st.markdown("---")
    col_stats, col_details = st.columns([1, 2])

    with col_stats:
        st.markdown("### 🔍 Wave Statistics")
    
        # Active Count Description Card
        if active_waves:
            is_alt = selected_count_name != "Primary Count (Highest Score)"
            title = "Alternate Count" if is_alt else "Primary Wave Structure"
            st.markdown(f"""
            <div class="metric-card">
                <h4>{title}</h4>
                <p style="font-size: 13px; color: #94A3B8;">Asset: <b>{active_symbol}</b></p>
                <p style="font-size: 13px; color: #94A3B8;">Degree: <b>{active_waves[0].degree}</b></p>
                <p style="font-size: 13px; color: #94A3B8;">Pricing Scale: <b>{'Logarithmic' if use_log else 'Linear'}</b></p>
            </div>
            """, unsafe_allow_html=True)
        
        # Unified Summary & Prediction Engine Panel
        payload = engine.get_summary_engine_payload(primary_count, alternates)
        if payload and payload.get("summary"):
            summary = payload["summary"]
            p_count = summary.get("primary_count")
        
            st.markdown(f"**Macro Degree Context:** `{summary.get('current_degree', 'Unknown')}`")
        
            if p_count:
                trend = p_count.get("trend", "Neutral")
                conf = p_count.get("confidence_score", 0.0)
                bias_color = "#10B981" if "Bullish" in trend else ("#EF4444" if "Bearish" in trend else "#F59E0B")
                bg_color = "rgba(16, 185, 129, 0.05)" if "Bullish" in trend else ("rgba(239, 68, 68, 0.05)" if "Bearish" in trend else "rgba(245, 158, 11, 0.05)")
            
                st.markdown(f"""
                <div style="background-color: {bg_color}; border-left: 4px solid {bias_color}; padding: 15px; border-radius: 4px; margin-bottom: 15px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                        <h4 style="color: {bias_color}; margin: 0;">🎯 Primary Count</h4>
                        <span style="color: {bias_color}; font-weight: bold; font-size: 14px;">{(conf*100):.0f}% Prob</span>
                    </div>
                    <p style="margin: 5px 0;"><b>Scenario:</b> {p_count.get('scenario')} ({p_count.get('larger_context')})</p>
                    <p style="margin: 5px 0; margin-bottom: 10px;"><b>Trend Bias:</b> <span style="color: {bias_color}; font-weight: 600;">{trend}</span></p>
                """, unsafe_allow_html=True)
            
                st.progress(conf)
            
                guidelines = p_count.get("guidelines_met", [])
                if guidelines:
                    gl_html = " ".join([f"<span style='background: rgba(59, 130, 246, 0.15); border: 1px solid rgba(59, 130, 246, 0.3); color: #60A5FA; padding: 2px 8px; border-radius: 12px; font-size: 11px; margin-right: 5px; display: inline-block; margin-bottom: 5px;'>{g}</span>" for g in guidelines])
                    st.markdown(f"<div style='margin: 10px 0;'>{gl_html}</div>", unsafe_allow_html=True)
            
                recent = p_count.get("recent_waves", [])
                if recent:
                    st.markdown("<p style='margin: 15px 0 5px 0; font-size: 13px; color: #94A3B8;'><b>Recent Wave Tiers:</b></p>", unsafe_allow_html=True)
                    tiers_html = " ".join([f"<span style='background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); padding: 3px 8px; border-radius: 4px; font-size: 12px; margin-right: 5px; display: inline-block; margin-bottom: 5px;'>{w['label']}: <b style='color:#fff;'>{w['tier_price']}</b></span>" for w in recent])
                    st.markdown(f"<div style='margin-bottom: 5px;'>{tiers_html}</div>", unsafe_allow_html=True)

                action = p_count.get("actionable", {})
                if action:
                    st.markdown(f"""
                    <div style="display: flex; justify-content: space-between; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 12px; margin-top: 12px; font-size: 14px;">
                        <div>🎯 Target: <b style="color: #fff;">{action.get('target_price', 'N/A')}</b></div>
                        <div>🛑 Inval: <b style="color: #fff;">{action.get('invalidation_level', 'N/A')}</b></div>
                        <div>⚖️ R:R: <b style="color: #fff;">1:{action.get('risk_reward_ratio', 'N/A')}</b></div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("</div>", unsafe_allow_html=True)
            
            a_count = summary.get("alternate_count")
            if a_count:
                a_trend = a_count.get("trend", "Neutral")
                a_conf = a_count.get("confidence_score", 0.0)
                a_color = "#10B981" if "Bullish" in a_trend else ("#EF4444" if "Bearish" in a_trend else "#F59E0B")
                a_bg_color = "rgba(16, 185, 129, 0.05)" if "Bullish" in a_trend else ("rgba(239, 68, 68, 0.05)" if "Bearish" in a_trend else "rgba(245, 158, 11, 0.05)")
            
                with st.expander(f"🔀 View Alternate Count ({(a_conf*100):.0f}% Prob)"):
                    st.markdown(f"""
                    <div style="background-color: {a_bg_color}; border-left: 4px solid {a_color}; padding: 15px; border-radius: 4px; margin-top: 5px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                            <h5 style="color: {a_color}; margin: 0;">🔄 Alternate Scenario</h5>
                            <span style="color: {a_color}; font-weight: bold; font-size: 13px;">{(a_conf*100):.0f}% Prob</span>
                        </div>
                        <p style="margin: 5px 0;"><b>Scenario:</b> {a_count.get('scenario')} ({a_count.get('larger_context')})</p>
                        <p style="margin: 5px 0; margin-bottom: 10px;"><b>Trend Bias:</b> <span style="color: {a_color}; font-weight: 600;">{a_trend}</span></p>
                    """, unsafe_allow_html=True)
                
                    st.progress(a_conf)
                
                    a_guidelines = a_count.get("guidelines_met", [])
                    if a_guidelines:
                        agl_html = " ".join([f"<span style='background: rgba(59, 130, 246, 0.15); border: 1px solid rgba(59, 130, 246, 0.3); color: #60A5FA; padding: 2px 8px; border-radius: 12px; font-size: 11px; margin-right: 5px; display: inline-block; margin-bottom: 5px;'>{g}</span>" for g in a_guidelines])
                        st.markdown(f"<div style='margin: 10px 0;'>{agl_html}</div>", unsafe_allow_html=True)
                
                    a_action = a_count.get("actionable", {})
                    if a_action:
                        st.markdown(f"""
                        <div style="display: flex; justify-content: space-between; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 10px; margin-top: 10px; font-size: 14px;">
                            <div>🎯 Target: <b style="color: #fff;">{a_action.get('target_price', 'N/A')}</b></div>
                            <div>🛑 Inval: <b style="color: #fff;">{a_action.get('invalidation_level', 'N/A')}</b></div>
                        </div>
                        """, unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)

    with col_details:
        # Analysis Tabs
        tab_rules, tab_fib, tab_counts = st.tabs(["📋 Rules Check", "📐 Fibonacci Ratios", "🔀 Alternates"])
    
        with tab_rules:
            st.markdown("#### Mechanical Verification Checklist")
            if active_waves:
                # Let's perform rule check on the active displayed waves
                # Find the last completed structural wave block (motive or corrective) to check rules
                last_block = find_last_wave_block(active_waves)
            
                # If motive block (5 waves)
                if len(last_block) == 5:
                    # Reconstruct pivot list from the wave nodes
                    pivs = [last_block[0].start_pivot] + [w.end_pivot for w in last_block]
                    is_valid, checklist = engine.verify_impulse_rules(pivs)
                
                    # Check alternation
                    v = engine._get_pivot_vals(pivs)
                    w2 = v[2] - v[1]
                    w4 = v[4] - v[3]
                    w1 = v[1] - v[0]
                    w3 = v[3] - v[2]
                    r2 = abs(w2)/abs(w1) if abs(w1) > 0 else 0
                    r4 = abs(w4)/abs(w3) if abs(w3) > 0 else 0
                    alt_passed = (r2 > 0.50 and r4 < 0.382) or (r2 < 0.382 and r4 > 0.50)
                    checklist.append({"rule": "Alternation Guideline (W2 deep, W4 shallow or vice versa)", "status": alt_passed})
                
                    for item in checklist:
                        icon = "✅" if item["status"] else ("⚠️" if "Alternation" in item["rule"] else "❌")
                        color = "#10B981" if item["status"] else ("#F59E0B" if "Alternation" in item["rule"] else "#EF4444")
                        st.markdown(f"<div style='padding: 8px 12px; margin: 6px 0; background: rgba(255,255,255,0.03); border-radius: 4px; border-left: 3px solid {color}; display: flex; align-items: center;'><span style='margin-right: 10px; font-size: 16px;'>{icon}</span> <span style='font-size: 14px; font-weight: 500;'>{item['rule']}</span></div>", unsafe_allow_html=True)
                else:
                    # Corrective block (3 waves)
                    pivs = [last_block[0].start_pivot] + [w.end_pivot for w in last_block]
                    if len(pivs) >= 4:
                        is_zz, zz_check = engine.verify_zigzag_rules(pivs[:4])
                        is_flat, flat_check = engine.verify_flat_rules(pivs[:4])
                    
                        if is_flat and not is_zz:
                            st.markdown("<p style='font-size:13px; color:#94A3B8; margin-bottom:10px;'>Validating as: <b>FLAT</b> Correction</p>", unsafe_allow_html=True)
                            checklist = flat_check
                        else:
                            st.markdown("<p style='font-size:13px; color:#94A3B8; margin-bottom:10px;'>Validating as: <b>ZIGZAG</b> Correction</p>", unsafe_allow_html=True)
                            checklist = zz_check
                        
                        for item in checklist:
                            icon = "✅" if item["status"] else ("⚠️" if "Guideline" in item["rule"] else "❌")
                            color = "#10B981" if item["status"] else ("#F59E0B" if "Guideline" in item["rule"] else "#EF4444")
                            st.markdown(f"<div style='padding: 8px 12px; margin: 6px 0; background: rgba(255,255,255,0.03); border-radius: 4px; border-left: 3px solid {color}; display: flex; align-items: center;'><span style='margin-right: 10px; font-size: 16px;'>{icon}</span> <span style='font-size: 14px; font-weight: 500;'>{item['rule']}</span></div>", unsafe_allow_html=True)
                    else:
                        st.info("Insufficient pivots to perform full structural rules validation on the active wave block.")
            else:
                st.info("No active waves labeled.")
            
        with tab_fib:
            st.markdown("#### Wave Relationships & Fib Proportions")
            last_block = find_last_wave_block(active_waves)
            if last_block and len(last_block) == 5:
                # Show actual calculated ratios
                pivs = [last_block[0].start_pivot] + [w.end_pivot for w in last_block]
                v = engine._get_pivot_vals(pivs)
                w1 = abs(v[1] - v[0])
                w2 = abs(v[2] - v[1])
                w3 = abs(v[3] - v[2])
                w4 = abs(v[4] - v[3])
                w5 = abs(v[5] - v[4])
            
                r2 = w2 / w1 if w1 > 0 else 0
                r3 = w3 / w1 if w1 > 0 else 0
                r4 = w4 / w3 if w3 > 0 else 0
                r5 = w5 / (v[3] - v[0]) if (v[3] - v[0]) > 0 else 0
            
                # Form HTML Table
                st.markdown(f"""
                <table>
                    <tr><th>Wave Relation</th><th>Calculated Ratio</th><th>Ideal Guideline</th></tr>
                    <tr><td>W2 / W1 (Retrace)</td><td><b>{r2:.1%}</b></td><td>50.0% - 78.6%</td></tr>
                    <tr><td>W3 / W1 (Extension)</td><td><b>{r3:.2f}x</b></td><td>1.618 - 2.618</td></tr>
                    <tr><td>W4 / W3 (Retrace)</td><td><b>{r4:.1%}</b></td><td>23.6% - 38.2%</td></tr>
                    <tr><td>W5 / Net W1-3</td><td><b>{r5:.1%}</b></td><td>61.8% - 100.0%</td></tr>
                </table>
                """, unsafe_allow_html=True)
            
                st.markdown("#### Fibonacci Retracement Levels")
                # Display Fib levels generated for W2 or W4
                for i, wave in enumerate(last_block):
                    if wave.fib_levels:
                        st.markdown(f"**Levels for Wave {wave.label}:**")
                        fib_df = pd.DataFrame([
                            {"Ratio": k, "Price": f"{v:,.2f}"} for k, v in wave.fib_levels.items()
                        ])
                        st.dataframe(fib_df, hide_index=True, use_container_width=True)
            else:
                st.info("Fibonacci ratio analysis is available for the most recent 5-wave motive sequence.")

        with tab_counts:
            st.markdown("#### Alternate Wave Interpretations")
            last_block = find_last_wave_block(primary_count)
            if len(last_block) == 5:
                score_pivs = [last_block[0].start_pivot] + [w.end_pivot for w in last_block]
                prim_score = engine.score_impulse(score_pivs)
            else:
                prim_score = 1.0
            st.markdown(f"**Primary Count Score:** `{prim_score:.1f}`")
            if alternates:
                for idx, alt in enumerate(alternates):
                    alt_block = find_last_wave_block(alt)
                    if len(alt_block) == 5:
                        alt_pivs = [alt_block[0].start_pivot] + [w.end_pivot for w in alt_block]
                        alt_score = engine.score_impulse(alt_pivs)
                    else:
                        alt_score = 1.0
                    st.markdown(f"**Alternate #{idx+1} Score:** `{alt_score:.1f}`")
            else:
                st.info("No valid alternate wave structures found.")

    # Display Data Details at Bottom of Page
    st.markdown("---")
    st.markdown("### 📊 Cleaned Historical Price Data")
    with st.expander("Expand to view historical daily records"):
        st.dataframe(df.sort_values('Date', ascending=False), use_container_width=True)


with tab_inst:
    st.markdown("## 🏦 Institutional Flow & Profile")
    st.markdown("The long-term mathematical structure and volume profile, stripped of time and noise.")
    
    from backend.institutional_engine import PointAndFigureEngine, VolumeProfileEngine
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    
    col_pnf, col_vp = st.columns([1, 1])
    
    with col_pnf:
        st.markdown("### Point & Figure (1% x 3)")
        pnf_engine = PointAndFigureEngine(df, box_size_pct=0.01, reversal_amount=3)
        pnf_cols = pnf_engine.calculate_pnf()
        
        if not pnf_cols:
            st.info("Not enough data to build P&F chart.")
        else:
            fig_pnf = go.Figure()
            for i, col in enumerate(pnf_cols):
                ctype = col["type"]
                boxes = col["boxes"]
                x_vals = [i] * len(boxes)
                color = "#10B981" if ctype == "X" else "#EF4444"
                symbol = "x" if ctype == "X" else "circle-open"
                
                fig_pnf.add_trace(go.Scatter(
                    x=x_vals,
                    y=boxes,
                    mode="markers",
                    marker=dict(symbol=symbol, color=color, size=10, line=dict(width=2, color=color)),
                    showlegend=False,
                    hoverinfo="y"
                ))
                
            fig_pnf.update_layout(
                plot_bgcolor='#0F172A',
                paper_bgcolor='#0B0F19',
                height=700,
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(
                    type="log" if use_log else "linear",
                    gridcolor='rgba(255, 255, 255, 0.1)',
                    gridwidth=1,
                    griddash='dot'
                ),
                margin=dict(l=20, r=20, t=20, b=20)
            )
            st.plotly_chart(fig_pnf, use_container_width=True)

    with col_vp:
        st.markdown("### Market Profile (Volume)")
        visible_df = df.tail(zoom_bars)
        vp_engine = VolumeProfileEngine(visible_df, bins=60)
        profile_data = vp_engine.calculate_profile()
        
        if not profile_data:
            st.info("Not enough data for Market Profile.")
        else:
            fig_vp = go.Figure()
            
            # Plot the histogram horizontally
            bins = profile_data["bins"]
            vols = profile_data["volume"]
            poc = profile_data["poc"]
            vah = profile_data["vah"]
            val = profile_data["val"]
            
            # Color value area distinctly
            colors = []
            for b in bins:
                if val <= b <= vah:
                    colors.append("rgba(59, 130, 246, 0.6)") # Value area (Blue)
                else:
                    colors.append("rgba(148, 163, 184, 0.2)") # Outside value area (Gray)
                    
            fig_vp.add_trace(go.Bar(
                y=bins,
                x=vols,
                orientation='h',
                marker_color=colors,
                showlegend=False,
                width=(bins[1]-bins[0])*0.9
            ))
            
            # Add POC Line
            fig_vp.add_hline(y=poc, line_color="#EF4444", line_width=2, annotation_text="POC", annotation_font=dict(color="#EF4444"))
            # Add VAH/VAL Lines
            fig_vp.add_hline(y=vah, line_color="#3B82F6", line_dash="dash", annotation_text="VAH", annotation_font=dict(color="#3B82F6"))
            fig_vp.add_hline(y=val, line_color="#3B82F6", line_dash="dash", annotation_text="VAL", annotation_font=dict(color="#3B82F6"))
            
            # Add Price line overlay
            fig_vp.add_trace(go.Scatter(
                y=visible_df['Close'],
                x=[max(vols)*0.1] * len(visible_df), # Draw it close to Y-axis
                mode="lines",
                line=dict(color="#FFFFFF", width=1),
                name="Price Path",
                opacity=0.3,
                showlegend=False
            ))

            fig_vp.update_layout(
                plot_bgcolor='#0F172A',
                paper_bgcolor='#0B0F19',
                height=700,
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(
                    type="log" if use_log else "linear",
                    gridcolor='rgba(255, 255, 255, 0.1)',
                    gridwidth=1,
                    griddash='dot'
                ),
                margin=dict(l=20, r=20, t=20, b=20)
            )
            st.plotly_chart(fig_vp, use_container_width=True)

