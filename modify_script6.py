with open("backend/wave_engine.py", "r") as f:
    content = f.read()

# Try memoizing verify_impulse_rules and verify_diagonal_rules to speed up _top_down_label
search = """    def verify_impulse_rules(self, pivots: List[Pivot]) -> Tuple[bool, List[Dict[str, Any]]]:
        \"\"\"Strict structural checks for 5-wave Impulse with Noise Tolerance.\"\"\"
        checklist = []
        if len(pivots) < 6:
            return False, []"""

replace = """    def verify_impulse_rules(self, pivots: List[Pivot]) -> Tuple[bool, List[Dict[str, Any]]]:
        \"\"\"Strict structural checks for 5-wave Impulse with Noise Tolerance.\"\"\"
        # Caching optimization
        if not hasattr(self, '_impulse_cache'):
            self._impulse_cache = {}

        # We can key by the sequence of pivot indices
        cache_key = tuple(p.index for p in pivots[:6]) if len(pivots) >= 6 else None
        if cache_key and cache_key in self._impulse_cache:
            return self._impulse_cache[cache_key]

        checklist = []
        if len(pivots) < 6:
            return False, []"""

search2 = """        # Final validation
        is_valid = direction_ok and rule_1 and rule_2 and rule_3
        return is_valid, checklist"""

replace2 = """        # Final validation
        is_valid = direction_ok and rule_1 and rule_2 and rule_3

        if cache_key:
            self._impulse_cache[cache_key] = (is_valid, checklist)

        return is_valid, checklist"""

new_content = content.replace(search, replace).replace(search2, replace2)

search3 = """    def verify_diagonal_rules(self, pivots: List[Pivot]) -> Tuple[bool, List[Dict[str, Any]]]:
        \"\"\"Checks rules for Leading/Ending Diagonals (allows overlap).\"\"\"
        checklist = []
        if len(pivots) < 6:
            return False, []"""

replace3 = """    def verify_diagonal_rules(self, pivots: List[Pivot]) -> Tuple[bool, List[Dict[str, Any]]]:
        \"\"\"Checks rules for Leading/Ending Diagonals (allows overlap).\"\"\"
        # Caching optimization
        if not hasattr(self, '_diagonal_cache'):
            self._diagonal_cache = {}

        cache_key = tuple(p.index for p in pivots[:6]) if len(pivots) >= 6 else None
        if cache_key and cache_key in self._diagonal_cache:
            return self._diagonal_cache[cache_key]

        checklist = []
        if len(pivots) < 6:
            return False, []"""

search4 = """        is_valid = direction_ok and rule_2 and rule_overlap and rule_convergence
        return is_valid, checklist"""

replace4 = """        is_valid = direction_ok and rule_2 and rule_overlap and rule_convergence

        if cache_key:
            self._diagonal_cache[cache_key] = (is_valid, checklist)

        return is_valid, checklist"""

new_content = new_content.replace(search3, replace3).replace(search4, replace4)

with open("backend/wave_engine.py", "w") as f:
    f.write(new_content)
