with open("backend/wave_engine.py", "r") as f:
    content = f.read()

search = """        # Extract to numpy arrays for O(1) loop access, ~100x faster than iloc
        highs = self.df['High'].values
        lows = self.df['Low'].values
        closes = self.df['Close'].values
        min_move_pcts = self.df['min_move_pct'].values
        dates = self.df['Date'].values
        log_highs = self.df['Log_High'].values
        log_lows = self.df['Log_Low'].values
        log_closes = self.df['Log_Close'].values"""

replace = """        # Extract to numpy arrays for O(1) loop access, ~100x faster than iloc
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
        log_closes = self._log_closes_values"""

new_content = content.replace(search, replace)

with open("backend/wave_engine.py", "w") as f:
    f.write(new_content)
