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
            vol = row['Volume']
            
            # TPO Fallback: If volume is 0, missing, or NaN (common for Yahoo Finance commodities),
            # we use Time Price Opportunity (TPO) counting by assigning a weight of 1 per day.
            if pd.isna(vol) or vol <= 0:
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
