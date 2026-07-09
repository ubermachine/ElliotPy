import re

with open("d:/antigravity_sandbox/ElliotPy/app.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Imports
content = content.replace(
    "import plotly.graph_objects as go",
    "import plotly.graph_objects as go\nfrom plotly.subplots import make_subplots"
)

# 2. add_wave_traces signature & degree check
content = content.replace(
    "def add_wave_traces(fig: go.Figure, wave: WaveNode, use_log: bool):",
    "def add_wave_traces(fig: go.Figure, wave: WaveNode, use_log: bool, degree_depth: int, show_confidence: bool):\n    degree_map = {'Cycle': 1, 'Primary': 2, 'Intermediate': 3, 'Minor': 4, 'Minuette': 5}\n    if degree_map.get(wave.degree, 6) > degree_depth:\n        return"
)

# 3. add_wave_traces Confidence Heatmap styling
styling_old = """    # Styling map for degrees
    if wave.degree == "Cycle":
        color = "#FF4A6B"  # Neon Coral/Red
        width = 3.5
        dash = 'solid'
    elif wave.degree == "Primary":
        color = "#00F0FF"  # Electric Blue/Cyan
        width = 3.0
        dash = 'solid'
    elif wave.degree == "Intermediate":
        color = "#FFC837"  # Gold
        width = 2.0
        dash = 'dash'
    elif wave.degree == "Minor":
        color = "#A0AEC0"  # Silver/Grey
        width = 2.0
        dash = 'dot'
    elif wave.degree == "Minute":
        color = "#F472B6"  # Pink
        width = 1.5
        dash = 'dashdot'
    elif wave.degree == "Minuette":
        color = "#9CA3AF"  # Grey
        width = 1.0
        dash = 'longdash'
    else:
        color = "#E2E8F0"
        width = 1.0
        dash = 'longdashdot'"""
        
styling_new = """    # Styling map for degrees
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
            dash = 'longdashdot'"""
content = content.replace(styling_old, styling_new)

# 4. Truncated Wave Label
content = content.replace(
    "    # Draw end pivot marker and text label\n    is_high = wave.end_pivot.type == \"HIGH\"",
    "    # Draw end pivot marker and text label\n    is_high = wave.end_pivot.type == \"HIGH\"\n    label_text = wave.label\n    if getattr(wave, 'is_truncated', False):\n        label_text += \" (Truncated)\""
)
content = content.replace(
    "text=[wave.label]",
    "text=[label_text]"
)

# 5. Row/Col in fig traces for add_wave_traces
content = content.replace(
    "hoverinfo='skip'\n    ))",
    "hoverinfo='skip'\n    ), row=1, col=1)"
)
content = content.replace(
    "hovertext=f\"<b>Wave {wave.label}</b><br>Degree: {wave.degree}<br>Price: {wave.end_pivot.price:,.2f}<br>Date: {wave.end_pivot.time}\"\n    ))",
    "hovertext=f\"<b>Wave {wave.label}</b><br>Degree: {wave.degree}<br>Price: {wave.end_pivot.price:,.2f}<br>Date: {wave.end_pivot.time}\"\n    ), row=1, col=1)"
)
content = content.replace(
    "hoverinfo='skip'\n        ))",
    "hoverinfo='skip'\n        ), row=1, col=1)"
)

# Recursive call update
content = content.replace(
    "add_wave_traces(fig, sw, use_log)",
    "add_wave_traces(fig, sw, use_log, degree_depth, show_confidence)"
)

# 6. Sidebar controls
sidebar_old = """st.sidebar.markdown("---")
st.sidebar.subheader("👁️ Display Options")
show_major_swings = st.sidebar.checkbox("Show Major Swings (T1)", value=True)"""
sidebar_new = """st.sidebar.markdown("---")
st.sidebar.subheader("👁️ Display Options")
degree_depth = st.sidebar.slider("Degree Depth (1-5):", min_value=1, max_value=5, value=5, help="1=Cycle/Primary only, 5=All sub-waves")
show_confidence = st.sidebar.toggle("Confidence Heatmap", value=False, help="Color code waves based on rule confidence score")
show_major_swings = st.sidebar.checkbox("Show Major Swings (T1)", value=True)"""
content = content.replace(sidebar_old, sidebar_new)

# 7. Make subplots
fig_old = "fig = go.Figure()"
fig_new = """fig = make_subplots(
    rows=2, cols=1, 
    shared_xaxes=True, 
    vertical_spacing=0.03, 
    row_heights=[0.75, 0.25]
)"""
content = content.replace(fig_old, fig_new)

# 8. Add row,col to Candlestick and Swings
content = content.replace(
    "line=dict(width=1)\n))",
    "line=dict(width=1)\n), row=1, col=1)"
)
content = content.replace(
    "showlegend=True\n    ))",
    "showlegend=True\n    ), row=1, col=1)"
)

# 9. Fallback active_waves
fallback_old = """active_waves = primary_count
if selected_count_name != "Primary Count (Highest Score)":
    alt_idx = int(selected_count_name.split("#")[-1]) - 1
    active_waves = alternates[alt_idx]"""
fallback_new = """active_waves = primary_count
if selected_count_name == "Primary Count (Highest Score)" and is_invalidated and alternates:
    st.warning("⚠️ Automatically falling back to Alternate Count #1 due to Primary Count invalidation.")
    active_waves = alternates[0]
elif selected_count_name != "Primary Count (Highest Score)":
    alt_idx = int(selected_count_name.split("#")[-1]) - 1
    active_waves = alternates[alt_idx]"""
content = content.replace(fallback_old, fallback_new)

# 10. Call add_wave_traces inside the loop
content = content.replace(
    "add_wave_traces(fig, wave, use_log)",
    "add_wave_traces(fig, wave, use_log, degree_depth, show_confidence)"
)

# 11. add_w5_projection needs row, col
content = content.replace(
    "name=\"W5 Target Zone\"\n    )",
    "name=\"W5 Target Zone\",\n        row=1, col=1\n    )"
)

# 12. add_parallel_channel needs row, col
# It has two scatter traces
content = content.replace(
    "hoverinfo='skip'\n    ))",
    "hoverinfo='skip'\n    ), row=1, col=1)"
) # wait, I already replaced this string earlier in add_wave_traces! 
# Let's write a regex or just replace specifically for add_parallel_channel.

# Actually, I'll write a Python script that replaces the rest
with open("d:/antigravity_sandbox/ElliotPy/app.py", "w", encoding="utf-8") as f:
    f.write(content)

