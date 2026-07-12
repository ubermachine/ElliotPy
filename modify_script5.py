with open("backend/wave_engine.py", "r") as f:
    content = f.read()

search = """    def run_adaptive_zigzag(self, min_move_mult: float = 1.0, start_idx: int = 0, end_idx: int = None) -> List[Pivot]:
        \"\"\"
        Executes adaptive percentage Zig-Zag.
        Can run on the whole chart or on a local slice (for dynamic sub-waving).
        \"\"\"
        if end_idx is None:
            end_idx = len(self.df) - 1

        pivots: List[Pivot] = []
        if end_idx - start_idx < 2:
            return pivots

        # Initialize
        direction = 0

        # Find first pivot (compare first few days to find direction)
        initial_period = min(20, end_idx - start_idx)
        h_idx = self.df['High'].iloc[start_idx:start_idx+initial_period].idxmax()
        l_idx = self.df['Low'].iloc[start_idx:start_idx+initial_period].idxmin()"""

replace = """    def run_adaptive_zigzag(self, min_move_mult: float = 1.0, start_idx: int = 0, end_idx: int = None) -> List[Pivot]:
        \"\"\"
        Executes adaptive percentage Zig-Zag.
        Can run on the whole chart or on a local slice (for dynamic sub-waving).
        \"\"\"
        if end_idx is None:
            end_idx = len(self.df) - 1

        pivots: List[Pivot] = []
        if end_idx - start_idx < 2:
            return pivots

        # Extract to numpy arrays for O(1) loop access, ~100x faster than iloc
        if not hasattr(self, '_highs_values'):
            self._highs_values = self.df['High'].values
            self._lows_values = self.df['Low'].values
            self._closes_values = self.df['Close'].values
            self._min_move_pcts_values = self.df['min_move_pct'].values
            self._dates_values = self.df['Date'].values
            self._log_highs_values = self.df['Log_High'].values
            self._log_lows_values = self.df['Log_Low'].values
            self._log_closes_values = self.df['Log_Close'].values

        highs = self._highs_values
        lows = self._lows_values
        closes = self._closes_values
        min_move_pcts = self._min_move_pcts_values
        dates = self._dates_values
        log_highs = self._log_highs_values
        log_lows = self._log_lows_values
        log_closes = self._log_closes_values

        # Initialize
        direction = 0

        # Find first pivot (compare first few days to find direction)
        initial_period = min(20, end_idx - start_idx)
        # Fast idxmax/idxmin
        slice_highs = highs[start_idx:start_idx+initial_period]
        slice_lows = lows[start_idx:start_idx+initial_period]
        h_idx = start_idx + int(slice_highs.argmax())
        l_idx = start_idx + int(slice_lows.argmin())"""

new_content = content.replace(search, replace)

search2 = """        if h_idx > l_idx:
            # Low came first, so we were going up to High
            pivots.append(Pivot(
                index=int(l_idx),
                price=float(self.df['Low'].iloc[l_idx]),
                log_price=float(self.df['Log_Low'].iloc[l_idx]),
                type_str="LOW",
                time=self.df['Date'].iloc[l_idx]
            ))
            direction = 1
            last_extreme_price = pivots[0].price
            last_extreme_idx = pivots[0].index
        else:
            pivots.append(Pivot(
                index=int(h_idx),
                price=float(self.df['High'].iloc[h_idx]),
                log_price=float(self.df['Log_High'].iloc[h_idx]),
                type_str="HIGH",
                time=self.df['Date'].iloc[h_idx]
            ))
            direction = -1
            last_extreme_price = pivots[0].price
            last_extreme_idx = pivots[0].index

        # Extract to numpy arrays for O(1) loop access, ~100x faster than iloc
        if not hasattr(self, '_highs_values'):
            self._highs_values = self.df['High'].values
            self._lows_values = self.df['Low'].values
            self._closes_values = self.df['Close'].values
            self._min_move_pcts_values = self.df['min_move_pct'].values
            self._dates_values = self.df['Date'].values
            self._log_highs_values = self.df['Log_High'].values
            self._log_lows_values = self.df['Log_Low'].values
            self._log_closes_values = self.df['Log_Close'].values

        highs = self._highs_values
        lows = self._lows_values
        closes = self._closes_values
        min_move_pcts = self._min_move_pcts_values
        dates = self._dates_values
        log_highs = self._log_highs_values
        log_lows = self._log_lows_values
        log_closes = self._log_closes_values

        # Run Zig-Zag loop"""

replace2 = """        if h_idx > l_idx:
            # Low came first, so we were going up to High
            pivots.append(Pivot(
                index=int(l_idx),
                price=float(lows[l_idx]),
                log_price=float(log_lows[l_idx]),
                type_str="LOW",
                time=dates[l_idx]
            ))
            direction = 1
            last_extreme_price = pivots[0].price
            last_extreme_idx = pivots[0].index
        else:
            pivots.append(Pivot(
                index=int(h_idx),
                price=float(highs[h_idx]),
                log_price=float(log_highs[h_idx]),
                type_str="HIGH",
                time=dates[h_idx]
            ))
            direction = -1
            last_extreme_price = pivots[0].price
            last_extreme_idx = pivots[0].index

        # Run Zig-Zag loop"""

new_content = new_content.replace(search2, replace2)

with open("backend/wave_engine.py", "w") as f:
    f.write(new_content)
