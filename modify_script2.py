with open("backend/wave_engine.py", "r") as f:
    content = f.read()

# Replace _get_atr_buffer content
search = """    def _get_atr_buffer(self, pivot: Pivot, multiplier: float = 0.3) -> float:
        atr = float(self.df['ATR'].iloc[pivot.index])
        if self.use_log_scale:
            close = float(self.df['Close'].iloc[pivot.index])
            return multiplier * (atr / close)
        return multiplier * atr"""

replace = """    def _get_atr_buffer(self, pivot: Pivot, multiplier: float = 0.3) -> float:
        # Cache ATR and Close arrays on the class instance if not already cached
        if not hasattr(self, '_atr_values'):
            self._atr_values = self.df['ATR'].values
            self._close_values = self.df['Close'].values

        atr = float(self._atr_values[pivot.index])
        if self.use_log_scale:
            close = float(self._close_values[pivot.index])
            return multiplier * (atr / close)
        return multiplier * atr"""

new_content = content.replace(search, replace)

with open("backend/wave_engine.py", "w") as f:
    f.write(new_content)
