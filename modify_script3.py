with open("backend/wave_engine.py", "r") as f:
    content = f.read()

# Make _get_pivot_vals faster, no pandas overhead since pivots log_price and price are properties
search = """    def _get_pivot_vals(self, pivots: List[Pivot]) -> List[float]:
        return [p.log_price if self.use_log_scale else p.price for p in pivots]"""

replace = """    def _get_pivot_vals(self, pivots: List[Pivot]) -> List[float]:
        return [p.log_price if self.use_log_scale else p.price for p in pivots]"""

# It's already just property access.
