import os

app_path = "d:/antigravity_sandbox/ElliotPy/app.py"
with open(app_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
skip = False
for line in lines:
    if "with tab_inst:" in line:
        skip = True
        break
    new_lines.append(line)

institutional_content = """with tab_inst:
    st.markdown("## 🏦 Institutional Flow & Profile")
    st.markdown("The long-term mathematical structure and volume profile, stripped of time and noise.")
    
    from backend.institutional_engine import PointAndFigureEngine, VolumeProfileEngine
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    
    # Calculate Data First for Summary
    pnf_engine = PointAndFigureEngine(df, box_size_pct=0.01, reversal_amount=3)
    pnf_cols = pnf_engine.calculate_pnf()
    
    visible_df = df.tail(zoom_bars)
    vp_engine = VolumeProfileEngine(visible_df, bins=60)
    profile_data = vp_engine.calculate_profile()
    
    # Render Summary
    if pnf_cols and profile_data:
        last_pnf_col = pnf_cols[-1]
        pnf_trend = "🟢 DEMAND CONTROL (Accumulation / Markup)" if last_pnf_col["type"] == "X" else "🔴 SUPPLY CONTROL (Distribution / Markdown)"
        
        last_close = visible_df['Close'].iloc[-1]
        vah = profile_data["vah"]
        val = profile_data["val"]
        poc = profile_data["poc"]
        
        if last_close > vah:
            profile_state = f"🟢 INITIATIVE BUYING (Price {last_close:,.2f} is breaking out above Value Area High {vah:,.2f})"
        elif last_close < val:
            profile_state = f"🔴 INITIATIVE SELLING (Price {last_close:,.2f} is breaking down below Value Area Low {val:,.2f})"
        else:
            profile_state = f"🟡 RESPONSIVE / BALANCED (Price {last_close:,.2f} is inside the Value Area, rotating around POC {poc:,.2f})"
            
        st.info(f"**P&F Trend Engine:** {pnf_trend}")
        st.info(f"**Market Profile Engine:** {profile_state}")
    
    st.markdown("---")
    
    col_pnf, col_vp = st.columns([1, 1])
    
    with col_pnf:
        st.markdown("### Point & Figure (1% x 3)")
        
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
"""

new_lines.append(institutional_content)

with open(app_path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)
