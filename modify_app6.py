import os

app_path = "d:/antigravity_sandbox/ElliotPy/app.py"
with open(app_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
skip = False

for line in lines:
    if "pnf_engine = PointAndFigureEngine(df, box_size_pct=0.01, reversal_amount=3)" in line:
        skip = True
    
    if skip and "st.plotly_chart(fig_vp, use_container_width=True)" in line:
        skip = False
        continue
    
    if not skip:
        new_lines.append(line)

replacement_idx = 0
for i, line in enumerate(new_lines):
    if "from plotly.subplots import make_subplots" in line:
        replacement_idx = i + 1

if replacement_idx > 0:
    charts_code = """
    import datetime
    
    # Filter data to strictly the last 3 months (90 days)
    last_date = df['Date'].iloc[-1]
    three_months_ago = last_date - datetime.timedelta(days=90)
    inst_df = df[df['Date'] >= three_months_ago].copy()
    
    date_range_str = f"{inst_df['Date'].iloc[0].strftime('%Y-%m-%d')} to {last_date.strftime('%Y-%m-%d')}"

    # Calculate Data First for Summary
    pnf_engine = PointAndFigureEngine(inst_df, box_size_pct=0.01, reversal_amount=3)
    pnf_cols = pnf_engine.calculate_pnf()
    
    vp_engine = VolumeProfileEngine(inst_df, bins=60)
    profile_data = vp_engine.calculate_profile()
    
    # Render Summary
    if pnf_cols and profile_data:
        last_pnf_col = pnf_cols[-1]
        pnf_trend = "🟢 DEMAND CONTROL (Accumulation / Markup)" if last_pnf_col["type"] == "X" else "🔴 SUPPLY CONTROL (Distribution / Markdown)"
        
        last_close = inst_df['Close'].iloc[-1]
        vah = profile_data["vah"]
        val = profile_data["val"]
        poc = profile_data["poc"]
        
        if last_close > vah:
            profile_state = f"🟢 INITIATIVE BUYING (Price {last_close:,.2f} is breaking out above Value Area High {vah:,.2f})"
        elif last_close < val:
            profile_state = f"🔴 INITIATIVE SELLING (Price {last_close:,.2f} is breaking down below Value Area Low {val:,.2f})"
        else:
            profile_state = f"🟡 RESPONSIVE / BALANCED (Price {last_close:,.2f} is inside the Value Area, rotating around POC {poc:,.2f})"
            
        st.info(f"**P&F Trend Engine (Last 3 Months):** {pnf_trend}")
        st.info(f"**Market Profile Engine (Last 3 Months):** {profile_state}")
    
    st.markdown("---")
    
    # --- POINT & FIGURE CHART ---
    st.markdown("### Point & Figure (1% x 3)")
    
    if not pnf_cols:
        st.info("Not enough data to build P&F chart for the last 3 months.")
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
                hoverinfo="y",
                name="P&F Column"
            ))
            
        fig_pnf.update_layout(
            title=f"Point & Figure Base (1% Box, 3-Box Reversal) | {date_range_str}",
            plot_bgcolor='#0F172A',
            paper_bgcolor='#0B0F19',
            height=600,
            xaxis=dict(
                title="Column Number (Time Independent)",
                showgrid=False, 
                zeroline=False, 
                showticklabels=True,
                color="rgba(255,255,255,0.6)"
            ),
            yaxis=dict(
                title="Price",
                type="log" if use_log else "linear",
                gridcolor='rgba(255, 255, 255, 0.1)',
                gridwidth=1,
                griddash='dot',
                showticklabels=True,
                side='right'
            ),
            margin=dict(l=20, r=60, t=60, b=40)
        )
        st.plotly_chart(fig_pnf, use_container_width=True)

    st.markdown("---")

    # --- MARKET PROFILE CHART ---
    st.markdown("### Market Profile (Volume TPOs)")
    
    if not profile_data:
        st.info("Not enough data for Market Profile in the last 3 months.")
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
                colors.append("rgba(59, 130, 246, 0.7)") # Value area (Blue)
            else:
                colors.append("rgba(148, 163, 184, 0.3)") # Outside value area (Gray)
                
        fig_vp.add_trace(go.Bar(
            y=bins,
            x=vols,
            orientation='h',
            marker_color=colors,
            name="Volume Profile",
            showlegend=False,
            width=(bins[1]-bins[0])*0.9
        ))
        
        # Add POC Line
        fig_vp.add_hline(y=poc, line_color="#EF4444", line_width=2, annotation_text=f"POC: {poc:.2f}", annotation_font=dict(color="#EF4444", size=12))
        # Add VAH/VAL Lines
        fig_vp.add_hline(y=vah, line_color="#3B82F6", line_dash="dash", annotation_text=f"VAH: {vah:.2f}", annotation_font=dict(color="#3B82F6", size=12))
        fig_vp.add_hline(y=val, line_color="#3B82F6", line_dash="dash", annotation_text=f"VAL: {val:.2f}", annotation_font=dict(color="#3B82F6", size=12))
        
        # Add Price line overlay
        fig_vp.add_trace(go.Scatter(
            y=inst_df['Close'],
            x=[max(vols)*0.05] * len(inst_df), # Draw it close to Y-axis
            mode="lines",
            line=dict(color="#FFFFFF", width=1.5),
            name="Closing Price Path",
            opacity=0.6,
            showlegend=True
        ))

        fig_vp.update_layout(
            title=f"Market Profile (Visible Range Volume) | {date_range_str}",
            plot_bgcolor='#0F172A',
            paper_bgcolor='#0B0F19',
            height=600,
            xaxis=dict(
                title="Accumulated Volume",
                showgrid=True, 
                gridcolor='rgba(255, 255, 255, 0.05)',
                zeroline=False, 
                showticklabels=True,
                color="rgba(255,255,255,0.6)"
            ),
            yaxis=dict(
                title="Price",
                type="log" if use_log else "linear",
                gridcolor='rgba(255, 255, 255, 0.1)',
                gridwidth=1,
                griddash='dot',
                showticklabels=True,
                side='right'
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            margin=dict(l=20, r=60, t=60, b=40)
        )
        st.plotly_chart(fig_vp, use_container_width=True)
"""
    
    # We replace from line 1011 (from plotly.subplots import make_subplots) to the end.
    # Wait, the skip logic deleted everything down to st.plotly_chart(fig_vp...)
    # So we just insert at replacement_idx.
    
    new_lines.insert(replacement_idx, charts_code)

with open(app_path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)
