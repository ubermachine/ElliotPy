import os

app_path = "d:/antigravity_sandbox/ElliotPy/app.py"
with open(app_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update Date Filter to 180 days (6 months)
content = content.replace("three_months_ago = last_date - datetime.timedelta(days=90)", 
                          "six_months_ago = last_date - datetime.timedelta(days=180)")
content = content.replace("inst_df = df[df['Date'] >= three_months_ago].copy()",
                          "inst_df = df[df['Date'] >= six_months_ago].copy()")

# 2. Update the Summary text to reflect 6 months instead of 3
content = content.replace("P&F Trend Engine (Last 3 Months)", "P&F Trend Engine (Last 6 Months)")
content = content.replace("Market Profile Engine (Last 3 Months)", "Market Profile Engine (Last 6 Months)")
content = content.replace("build P&F chart for the last 3 months.", "build P&F chart for the last 6 months.")
content = content.replace("Market Profile in the last 3 months.", "Market Profile in the last 6 months.")

# 3. Inject P&F Signal Calculation right after `pnf_cols = pnf_engine.calculate_pnf()`
sig_injection = """    pnf_cols = pnf_engine.calculate_pnf()
    pnf_sig = pnf_engine.calculate_signals_and_targets(pnf_cols)"""
content = content.replace("    pnf_cols = pnf_engine.calculate_pnf()", sig_injection)

# 4. Inject Signal rendering into the Summary Block
old_summary_rendering = """        st.info(f"**P&F Trend Engine (Last 6 Months):** {pnf_trend}")"""
new_summary_rendering = """        signal_text = f" | ⚡ **{pnf_sig['signal']}** (Target: {pnf_sig['target']:.2f})" if pnf_sig['signal'] else ""
        st.info(f"**P&F Trend Engine (Last 6 Months):** {pnf_trend}{signal_text}")"""
content = content.replace(old_summary_rendering, new_summary_rendering)


# 5. Inject Target Line and Marker into the P&F Chart Layout
old_fig_pnf = """        fig_pnf.update_layout("""
new_fig_pnf = """
        if pnf_sig['signal']:
            # Draw Target Line
            fig_pnf.add_hline(y=pnf_sig['target'], line_dash="dash", line_color="#F59E0B", line_width=2,
                              annotation_text=f"🎯 Target: {pnf_sig['target']:.2f}",
                              annotation_font=dict(color="#F59E0B", size=12))
            
            # Draw Breakout Marker
            breakout_col = pnf_sig['breakout_col']
            is_buy = "BUY" in pnf_sig['signal']
            marker_y = max(pnf_cols[breakout_col]['boxes']) if is_buy else min(pnf_cols[breakout_col]['boxes'])
            marker_color = "#10B981" if is_buy else "#EF4444"
            marker_symbol = "triangle-up" if is_buy else "triangle-down"
            
            fig_pnf.add_trace(go.Scatter(
                x=[breakout_col],
                y=[marker_y],
                mode="markers",
                marker=dict(symbol=marker_symbol, color=marker_color, size=16),
                showlegend=False,
                hovertext=pnf_sig['signal']
            ))

        fig_pnf.update_layout("""
content = content.replace(old_fig_pnf, new_fig_pnf)

with open(app_path, "w", encoding="utf-8") as f:
    f.write(content)
