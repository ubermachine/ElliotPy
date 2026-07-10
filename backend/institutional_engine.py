import pandas as pd
import numpy as np
from typing import List, Dict, Any, Tuple

class VolumeProfileEngine:
    def __init__(self, df: pd.DataFrame, bins: int = 50):
        self.df = df
        self.bins = bins

    def calculate_profile(self) -> Dict[str, Any]:
        if self.df.empty:
            return {}

        min_price = self.df['Low'].min()
        max_price = self.df['High'].max()
        
        if min_price == max_price:
            return {}
            
        # Create bins
        bin_edges = np.linspace(min_price, max_price, self.bins + 1)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        volume_profile = np.zeros(self.bins)

        for _, row in self.df.iterrows():
            low = row['Low']
            high = row['High']
            
            # PERMANENT TPO OVERRIDE: 
            # Ignore real volume (which is often flawed/missing for commodities) 
            # and use Time Price Opportunity (TPO) counting.
            vol = 1.0
            
            if high == low:
                # Add to single bin
                idx = np.digitize(high, bin_edges) - 1
                if 0 <= idx < self.bins:
                    volume_profile[idx] += vol
                continue

            # Distribute volume across intersecting bins
            intersecting_mask = (bin_edges[:-1] <= high) & (bin_edges[1:] >= low)
            intersecting_bins = np.where(intersecting_mask)[0]
            if len(intersecting_bins) > 0:
                vol_per_bin = vol / len(intersecting_bins)
                for idx in intersecting_bins:
                    volume_profile[idx] += vol_per_bin

        # Find POC (Point of Control)
        poc_idx = np.argmax(volume_profile)
        poc_price = bin_centers[poc_idx]
        poc_vol = volume_profile[poc_idx]

        # Calculate Value Area (70% of total volume)
        total_vol = np.sum(volume_profile)
        target_vol = total_vol * 0.70
        
        va_vol = poc_vol
        upper_idx = poc_idx
        lower_idx = poc_idx

        while va_vol < target_vol:
            up_vol = volume_profile[upper_idx + 1] if upper_idx < self.bins - 1 else -1
            down_vol = volume_profile[lower_idx - 1] if lower_idx > 0 else -1

            if up_vol == -1 and down_vol == -1:
                break

            if up_vol >= down_vol:
                upper_idx += 1
                va_vol += up_vol
            else:
                lower_idx -= 1
                va_vol += down_vol

        vah_price = bin_centers[upper_idx]
        val_price = bin_centers[lower_idx]

        return {
            "bins": bin_centers.tolist(),
            "volume": volume_profile.tolist(),
            "poc": poc_price,
            "vah": vah_price,
            "val": val_price,
            "total_volume": total_vol
        }


class PointAndFigureEngine:
    def __init__(self, df: pd.DataFrame, box_size_pct: float = 0.01, reversal_amount: int = 3):
        self.df = df
        # We use natural log for percentage-based box sizes. 
        self.box_size = np.log1p(box_size_pct)
        self.reversal = reversal_amount * self.box_size

    def calculate_pnf(self) -> List[Dict[str, Any]]:
        if self.df.empty:
            return []

        columns = []
        first_close = np.log(self.df['Close'].iloc[0])
        current_trend = None
        current_box_price = first_close
        current_col = []

        for _, row in self.df.iterrows():
            high = np.log(row['High'])
            low = np.log(row['Low'])
            
            if current_trend is None:
                if high >= current_box_price + self.box_size:
                    current_trend = 'X'
                    boxes = np.arange(current_box_price, high, self.box_size)
                    current_col.extend(boxes)
                    current_box_price = current_col[-1] if len(current_col) > 0 else current_box_price
                elif low <= current_box_price - self.box_size:
                    current_trend = 'O'
                    boxes = np.arange(current_box_price, low, -self.box_size)
                    current_col.extend(boxes)
                    current_box_price = current_col[-1] if len(current_col) > 0 else current_box_price
                continue

            if current_trend == 'X':
                if high >= current_box_price + self.box_size:
                    num_boxes = int((high - current_box_price) / self.box_size)
                    new_boxes = [current_box_price + (i * self.box_size) for i in range(1, num_boxes + 1)]
                    current_col.extend(new_boxes)
                    current_box_price = current_col[-1]
                elif low <= current_box_price - self.reversal:
                    if current_col:
                        columns.append({"type": "X", "boxes": [np.exp(b) for b in current_col]})
                    current_trend = 'O'
                    start_box = current_box_price - self.box_size
                    num_boxes = int((start_box - low) / self.box_size)
                    current_col = [start_box - (i * self.box_size) for i in range(num_boxes + 1)]
                    current_box_price = current_col[-1] if len(current_col) > 0 else start_box

            elif current_trend == 'O':
                if low <= current_box_price - self.box_size:
                    num_boxes = int((current_box_price - low) / self.box_size)
                    new_boxes = [current_box_price - (i * self.box_size) for i in range(1, num_boxes + 1)]
                    current_col.extend(new_boxes)
                    current_box_price = current_col[-1]
                elif high >= current_box_price + self.reversal:
                    if current_col:
                        columns.append({"type": "O", "boxes": [np.exp(b) for b in current_col]})
                    current_trend = 'X'
                    start_box = current_box_price + self.box_size
                    num_boxes = int((high - start_box) / self.box_size)
                    current_col = [start_box + (i * self.box_size) for i in range(num_boxes + 1)]
                    current_box_price = current_col[-1] if len(current_col) > 0 else start_box

        if current_col:
            columns.append({"type": current_trend, "boxes": [np.exp(b) for b in current_col]})

        return columns

    def calculate_signals_and_targets(self, columns: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyzes P&F columns to detect the most recent Double Top / Bottom breakout
        and calculates horizontal targets based on the preceding congestion base width.
        """
        if len(columns) < 3:
            return {"signal": None, "target": None, "base_width": 0, "breakout_col": -1}
            
        signal = None
        target = None
        base_width = 0
        breakout_col_idx = -1
        
        # We iterate backwards to find the most recent valid signal
        for i in range(len(columns)-1, 1, -1):
            curr = columns[i]
            prev = columns[i-1]
            prev2 = columns[i-2]
            
            # Double Top Buy Signal
            if curr["type"] == "X" and prev2["type"] == "X":
                if max(curr["boxes"]) > max(prev2["boxes"]):
                    # We found a breakout. Now find base width.
                    resistance = max(prev2["boxes"])
                    support = min(prev["boxes"])
                    width = 2
                    lowest_base_price = support
                    for j in range(i-3, -1, -1):
                        if columns[j]["type"] == "X" and max(columns[j]["boxes"]) > resistance:
                            break
                        if columns[j]["type"] == "O" and min(columns[j]["boxes"]) < support:
                            lowest_base_price = min(columns[j]["boxes"])
                        width += 1
                        
                    # Aggressive Wyckoff Target: Lowest price of base + (Width * Reversal * Box Size)
                    log_low = np.log(lowest_base_price)
                    log_target = log_low + (width * self.reversal)
                    
                    signal = "Double Top Breakout (BUY)"
                    target = np.exp(log_target)
                    base_width = width
                    breakout_col_idx = i
                    break
                    
            # Double Bottom Sell Signal
            elif curr["type"] == "O" and prev2["type"] == "O":
                if min(curr["boxes"]) < min(prev2["boxes"]):
                    support = min(prev2["boxes"])
                    resistance = max(prev["boxes"])
                    width = 2
                    highest_base_price = resistance
                    for j in range(i-3, -1, -1):
                        if columns[j]["type"] == "O" and min(columns[j]["boxes"]) < support:
                            break
                        if columns[j]["type"] == "X" and max(columns[j]["boxes"]) > resistance:
                            highest_base_price = max(columns[j]["boxes"])
                        width += 1
                        
                    log_high = np.log(highest_base_price)
                    log_target = log_high - (width * self.reversal)
                    
                    signal = "Double Bottom Breakdown (SELL)"
                    target = np.exp(log_target)
                    base_width = width
                    breakout_col_idx = i
                    break
                    
        return {
            "signal": signal,
            "target": target,
            "base_width": base_width,
            "breakout_col": breakout_col_idx
        }
