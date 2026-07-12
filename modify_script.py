import re

with open("backend/wave_engine.py", "r") as f:
    content = f.read()

# Replace run_adaptive_zigzag content
def replace_run_adaptive_zigzag(text):
    # This might be tricky, let's use string replace for the loop part
    search = """        # Run Zig-Zag loop
        for t in range(int(last_extreme_idx) + 1, end_idx + 1):
            current_close = float(self.df['Close'].iloc[t])
            current_high = float(self.df['High'].iloc[t])
            current_low = float(self.df['Low'].iloc[t])
            threshold = float(self.df['min_move_pct'].iloc[t]) * min_move_mult

            if direction == 1:  # Looking for HIGH
                if current_high > last_extreme_price:
                    last_extreme_price = current_high
                    last_extreme_idx = t

                if current_low <= last_extreme_price * (1.0 - threshold):
                    pivots.append(Pivot(
                        index=int(last_extreme_idx),
                        price=float(self.df['High'].iloc[last_extreme_idx]),
                        log_price=float(self.df['Log_High'].iloc[last_extreme_idx]),
                        type_str="HIGH",
                        time=self.df['Date'].iloc[last_extreme_idx]
                    ))
                    direction = -1
                    last_extreme_price = current_low
                    last_extreme_idx = t

            elif direction == -1:  # Looking for LOW
                if current_low < last_extreme_price:
                    last_extreme_price = current_low
                    last_extreme_idx = t

                if current_high >= last_extreme_price * (1.0 + threshold):
                    pivots.append(Pivot(
                        index=int(last_extreme_idx),
                        price=float(self.df['Low'].iloc[last_extreme_idx]),
                        log_price=float(self.df['Log_Low'].iloc[last_extreme_idx]),
                        type_str="LOW",
                        time=self.df['Date'].iloc[last_extreme_idx]
                    ))
                    direction = 1
                    last_extreme_price = current_high
                    last_extreme_idx = t

        # Append last bar as a temporary pivot to anchor the current leg
        if pivots and pivots[-1].index != end_idx:
            last_close = float(self.df['Close'].iloc[end_idx])
            last_type = "HIGH" if pivots[-1].type == "LOW" else "LOW"
            pivots.append(Pivot(
                index=end_idx,
                price=last_close,
                log_price=float(self.df['Log_Close'].iloc[end_idx]),
                type_str=last_type,
                time=self.df['Date'].iloc[end_idx]
            ))"""

    replace = """        # Extract to numpy arrays for O(1) loop access, ~100x faster than iloc
        highs = self.df['High'].values
        lows = self.df['Low'].values
        closes = self.df['Close'].values
        min_move_pcts = self.df['min_move_pct'].values
        dates = self.df['Date'].values
        log_highs = self.df['Log_High'].values
        log_lows = self.df['Log_Low'].values
        log_closes = self.df['Log_Close'].values

        # Run Zig-Zag loop
        for t in range(int(last_extreme_idx) + 1, end_idx + 1):
            current_close = float(closes[t])
            current_high = float(highs[t])
            current_low = float(lows[t])
            threshold = float(min_move_pcts[t]) * min_move_mult

            if direction == 1:  # Looking for HIGH
                if current_high > last_extreme_price:
                    last_extreme_price = current_high
                    last_extreme_idx = t

                if current_low <= last_extreme_price * (1.0 - threshold):
                    pivots.append(Pivot(
                        index=int(last_extreme_idx),
                        price=float(highs[last_extreme_idx]),
                        log_price=float(log_highs[last_extreme_idx]),
                        type_str="HIGH",
                        time=dates[last_extreme_idx]
                    ))
                    direction = -1
                    last_extreme_price = current_low
                    last_extreme_idx = t

            elif direction == -1:  # Looking for LOW
                if current_low < last_extreme_price:
                    last_extreme_price = current_low
                    last_extreme_idx = t

                if current_high >= last_extreme_price * (1.0 + threshold):
                    pivots.append(Pivot(
                        index=int(last_extreme_idx),
                        price=float(lows[last_extreme_idx]),
                        log_price=float(log_lows[last_extreme_idx]),
                        type_str="LOW",
                        time=dates[last_extreme_idx]
                    ))
                    direction = 1
                    last_extreme_price = current_high
                    last_extreme_idx = t

        # Append last bar as a temporary pivot to anchor the current leg
        if pivots and pivots[-1].index != end_idx:
            last_close = float(closes[end_idx])
            last_type = "HIGH" if pivots[-1].type == "LOW" else "LOW"
            pivots.append(Pivot(
                index=end_idx,
                price=last_close,
                log_price=float(log_closes[end_idx]),
                type_str=last_type,
                time=dates[end_idx]
            ))"""

    return text.replace(search, replace)

new_content = replace_run_adaptive_zigzag(content)

with open("backend/wave_engine.py", "w") as f:
    f.write(new_content)
