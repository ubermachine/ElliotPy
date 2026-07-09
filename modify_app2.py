import re

with open("d:/antigravity_sandbox/ElliotPy/app.py", "r", encoding="utf-8") as f:
    content = f.read()

# Fix add_parallel_channel
content = re.sub(
    r"(name=\"Channel Top\",\s*showlegend=False,\s*hoverinfo='skip'\n\s*\))",
    r"\1, row=1, col=1",
    content
)
content = re.sub(
    r"(name=\"Channel Bottom\",\s*showlegend=False,\s*hoverinfo='skip'\n\s*\))",
    r"\1, row=1, col=1",
    content
)

# Fix Invalidation Line
content = re.sub(
    r"(annotation_font=dict\(color=\"#FF003C\", size=10\)\n\s*\))",
    r"\1, row=1, col=1",
    content
)

# Add RSI trace before layout
rsi_trace = """# Add RSI Trace
if 'RSI' in df.columns:
    fig.add_trace(go.Scatter(
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
            fig.add_trace(go.Scatter(
                x=[w3.end_pivot.time, w5.end_pivot.time],
                y=[df['RSI'].iloc[w3.end_pivot.index], df['RSI'].iloc[w5.end_pivot.index]],
                mode='lines', line=dict(color='yellow', width=2, dash='dot'),
                showlegend=False
            ), row=2, col=1)

# Calculate visible Y-range"""
content = content.replace("# Calculate visible Y-range", rsi_trace)

# Update layout
layout_old = """    yaxis=dict(
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
    plot_bgcolor='#0F172A',"""
layout_new = """    yaxis=dict(
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
    plot_bgcolor='#0F172A',"""
content = content.replace(layout_old, layout_new)

with open("d:/antigravity_sandbox/ElliotPy/app.py", "w", encoding="utf-8") as f:
    f.write(content)
