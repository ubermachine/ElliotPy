import os
import re

app_path = "d:/antigravity_sandbox/ElliotPy/app.py"
with open(app_path, "r", encoding="utf-8") as f:
    content = f.read()

# For P&F Chart
pnf_range_code = """
        y_min_pnf = float(inst_df['Low'].min()) * 0.95
        y_max_pnf = float(inst_df['High'].max()) * 1.05
        if use_log:
            pnf_y_range = [np.log10(y_min_pnf), np.log10(y_max_pnf)]
        else:
            pnf_y_range = [y_min_pnf, y_max_pnf]
            
        fig_pnf.update_layout("""

content = content.replace("        fig_pnf.update_layout(", pnf_range_code)

pnf_yaxis_old = """            yaxis=dict(
                title="Price",
                type="log" if use_log else "linear",
                gridcolor='rgba(255, 255, 255, 0.1)',
                gridwidth=1,
                griddash='dot',
                showticklabels=True,
                side='right'
            ),"""
pnf_yaxis_new = """            yaxis=dict(
                title="Price",
                type="log" if use_log else "linear",
                gridcolor='rgba(255, 255, 255, 0.1)',
                gridwidth=1,
                griddash='dot',
                showticklabels=True,
                side='right',
                range=pnf_y_range
            ),"""
content = content.replace(pnf_yaxis_old, pnf_yaxis_new)


# For Market Profile Chart
vp_range_code = """
        y_min_vp = float(inst_df['Low'].min()) * 0.95
        y_max_vp = float(inst_df['High'].max()) * 1.05
        if use_log:
            vp_y_range = [np.log10(y_min_vp), np.log10(y_max_vp)]
        else:
            vp_y_range = [y_min_vp, y_max_vp]
            
        fig_vp.update_layout("""
content = content.replace("        fig_vp.update_layout(", vp_range_code)

vp_yaxis_old = """            yaxis=dict(
                title="Price",
                type="log" if use_log else "linear",
                gridcolor='rgba(255, 255, 255, 0.1)',
                gridwidth=1,
                griddash='dot',
                showticklabels=True,
                side='right'
            ),"""
vp_yaxis_new = """            yaxis=dict(
                title="Price",
                type="log" if use_log else "linear",
                gridcolor='rgba(255, 255, 255, 0.1)',
                gridwidth=1,
                griddash='dot',
                showticklabels=True,
                side='right',
                range=vp_y_range
            ),"""
content = content.replace(vp_yaxis_old, vp_yaxis_new)

with open(app_path, "w", encoding="utf-8") as f:
    f.write(content)
