import numpy as np
import pandas as pd
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
class Pivot:
    def __init__(self, index: int, price: float, log_price: float, type_str: str, time: Any):
        self.index = index
        self.price = price
        self.log_price = log_price
        self.type = type_str  # "HIGH" or "LOW"
        self.time = time

    def __repr__(self):
        return f"Pivot({self.index}, {self.price:.2f}, {self.type})"


class WaveNode:
    def __init__(self, start_pivot: Pivot, end_pivot: Pivot, label: str, degree: str, wave_type: str = "motive"):
        self.start_pivot = start_pivot
        self.end_pivot = end_pivot
        self.label = label
        self.degree = degree
        self.wave_type = wave_type
        self.sub_waves: List['WaveNode'] = []
        
        # UI overlays
        self.fib_levels: Dict[str, float] = {}
        self.channel_lines: List[Tuple[Tuple[int, float], Tuple[int, float]]] = []
        self.invalidation_price: Optional[float] = None
        self.score: float = 0.0
        self.is_truncated: bool = False
        self.time_invalidated: bool = False
        self.rule_checklist: List[Dict[str, Any]] = []

    def get_duration(self) -> int:
        return self.end_pivot.index - self.start_pivot.index

    def get_price_range(self, use_log: bool = False) -> float:
        v_start = self.start_pivot.log_price if use_log else self.start_pivot.price
        v_end = self.end_pivot.log_price if use_log else self.end_pivot.price
        return abs(v_end - v_start)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "degree": self.degree,
            "wave_type": self.wave_type,
            "start": {
                "index": int(self.start_pivot.index),
                "price": float(self.start_pivot.price),
                "type": self.start_pivot.type,
                "time": str(self.start_pivot.time)
            },
            "end": {
                "index": int(self.end_pivot.index),
                "price": float(self.end_pivot.price),
                "type": self.end_pivot.type,
                "time": str(self.end_pivot.time)
            },
            "sub_waves": [sw.to_dict() for sw in self.sub_waves],
            "fib_levels": {k: float(v) for k, v in self.fib_levels.items()},
            "invalidation_price": float(self.invalidation_price) if self.invalidation_price is not None else None,
            "score": float(self.score),
            "rule_checklist": self.rule_checklist
        }


@dataclass
class CandidateCount:
    """Represents a candidate wave count from one ZigZag resolution + window size."""
    waves: List['WaveNode']
    score: float
    resolution: float
    window_size: int
    pattern_type: str          # 'impulse', 'diagonal', 'corrective'
    invalidation: Optional[float]
    anchor_start_idx: int
    anchor_end_idx: int


class DailyElliottWaveEngine:
    DEGREE_LABELS = {
        "Cycle": {"motive": ["I", "II", "III", "IV", "V"], "corrective": ["A", "B", "C"], "diagonal": ["A", "B", "C", "D", "E"]},
        "Primary": {"motive": ["[1]", "[2]", "[3]", "[4]", "[5]"], "corrective": ["[A]", "[B]", "[C]"], "diagonal": ["[A]", "[B]", "[C]", "[D]", "[E]"]},
        "Intermediate": {"motive": ["(1)", "(2)", "(3)", "(4)", "(5)"], "corrective": ["(A)", "(B)", "(C)"], "diagonal": ["(A)", "(B)", "(C)", "(D)", "(E)"]},
        "Minor": {"motive": ["{1}", "{2}", "{3}", "{4}", "{5}"], "corrective": ["{A}", "{B}", "{C}"], "diagonal": ["{A}", "{B}", "{C}", "{D}", "{E}"]},
        "Minuette": {"motive": ["i", "ii", "iii", "iv", "v"], "corrective": ["a", "b", "c"], "diagonal": ["a", "b", "c", "d", "e"]}
    }

    DEGREE_ORDER = ["Cycle", "Primary", "Intermediate", "Minor", "Minuette"]

    def __init__(self, df: pd.DataFrame, use_log_scale: bool = False):
        self.df = df.copy()
        self.use_log_scale = use_log_scale
        
        # Prep price arrays
        self.df['Log_Close'] = np.log(self.df['Close'])
        self.df['Log_High'] = np.log(self.df['High'])
        self.df['Log_Low'] = np.log(self.df['Low'])
        self.df['Log_Open'] = np.log(self.df['Open'])
        
        # Calculate ATR_14
        self.df['ATR'] = self._calculate_atr_14()
        self.df['RSI'] = self._calculate_rsi_14()
        macd_line, signal_line, histogram = self._calculate_macd()
        self.df['MACD'] = macd_line
        self.df['MACD_Signal'] = signal_line
        self.df['MACD_Hist'] = histogram

        # Calculate adaptive Zig-Zag thresholds per bar
        # Pure ATR sensitivity (no arbitrary % floors) prevents "big guess" waves
        self.df['min_move_pct'] = (self.df['ATR'] / self.df['Close']) * 1.2

    def _calculate_rsi_14(self) -> pd.Series:
        delta = self.df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        rs = gain / loss.replace(0, np.nan)
        return 100 - (100 / (1 + rs))

    def _calculate_macd(self, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculates MACD Line, Signal Line, and Histogram."""
        ema_fast = self.df['Close'].ewm(span=fast, adjust=False).mean()
        ema_slow = self.df['Close'].ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram

    def _calculate_atr_14(self) -> pd.Series:
        high = self.df['High']
        low = self.df['Low']
        close = self.df['Close'].shift(1)
        
        tr1 = high - low
        tr2 = (high - close).abs()
        tr3 = (low - close).abs()
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=14, min_periods=1).mean()

    def run_adaptive_zigzag(self, min_move_mult: float = 1.0, start_idx: int = 0, end_idx: int = None) -> List[Pivot]:
        """
        Executes adaptive percentage Zig-Zag.
        Can run on the whole chart or on a local slice (for dynamic sub-waving).
        """
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
        l_idx = self.df['Low'].iloc[start_idx:start_idx+initial_period].idxmin()
        
        if h_idx > l_idx:
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

        # Run Zig-Zag loop
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
            ))
            
        return pivots

    def run_multi_resolution_zigzag(self, base_mult: float = 1.0) -> Dict[float, List[Pivot]]:
        """Runs ZigZag at multiple ATR sensitivity levels to capture macro and micro structure."""
        multipliers = [base_mult * 0.5, base_mult, base_mult * 2.0, base_mult * 3.0]
        pivot_sets = {}
        for mult in multipliers:
            pivots = self.run_adaptive_zigzag(mult)
            pivot_sets[float(mult)] = pivots
        return pivot_sets

    def _generate_candidates(self, pivot_sets: Dict[float, List[Pivot]]) -> List[CandidateCount]:
        """Generates candidate wave counts from multiple resolutions and window sizes."""
        candidates = []
        chart_range = self.df['Close'].max() - self.df['Close'].min()
        min_range = chart_range * 0.05  # Skip tiny structures

        for resolution, pivots in pivot_sets.items():
            n = len(pivots)
            for window_size in [6, 8, 10, 12]:
                if n < window_size:
                    continue
                for i in range(n - window_size + 1):
                    window = pivots[i:i + window_size]
                    price_range = abs(window[-1].price - window[0].price)
                    if price_range < min_range:
                        continue

                    # For window_size == 6, test directly
                    if window_size == 6:
                        test_pivots = window
                    else:
                        # Extract 6 most significant pivots from larger window
                        test_pivots = self._extract_significant_pivots(window, count=6)
                        if len(test_pivots) < 6:
                            continue

                    # Try impulse
                    is_imp, checklist = self.verify_impulse_rules(test_pivots)
                    if is_imp:
                        score = self.score_impulse(test_pivots)
                        inv = test_pivots[0].price if (test_pivots[1].price > test_pivots[0].price) else test_pivots[0].price
                        candidates.append(CandidateCount(
                            waves=[], score=score, resolution=resolution,
                            window_size=window_size, pattern_type="impulse",
                            invalidation=inv,
                            anchor_start_idx=test_pivots[0].index,
                            anchor_end_idx=test_pivots[-1].index
                        ))

                    # Try diagonal
                    is_diag, _ = self.verify_diagonal_rules(test_pivots)
                    if is_diag and not is_imp:
                        score = self.score_diagonal(test_pivots)
                        candidates.append(CandidateCount(
                            waves=[], score=score, resolution=resolution,
                            window_size=window_size, pattern_type="diagonal",
                            invalidation=test_pivots[0].price,
                            anchor_start_idx=test_pivots[0].index,
                            anchor_end_idx=test_pivots[-1].index
                        ))

        return candidates

    def _rank_candidates(self, candidates: List['CandidateCount']) -> List['CandidateCount']:
        """Ranks candidates by composite score, deduplicates overlapping structures."""
        if not candidates:
            return []

        total_bars = len(self.df)
        current_price = float(self.df['Close'].iloc[-1])

        # Apply bonuses and penalties
        for c in candidates:
            recency_bonus = (c.anchor_end_idx / max(total_bars, 1)) * 5.0
            c.score += recency_bonus

            if c.invalidation is not None and c.invalidation < current_price * 0.5:
                c.score -= 5.0  # Penalize stale invalidation levels

        # Sort by score descending
        candidates.sort(key=lambda c: c.score, reverse=True)

        # Deduplicate: remove candidates with >70% index overlap with higher-scored ones
        kept = []
        for c in candidates:
            overlap = False
            for k in kept:
                # Calculate overlap ratio
                overlap_start = max(c.anchor_start_idx, k.anchor_start_idx)
                overlap_end = min(c.anchor_end_idx, k.anchor_end_idx)
                if overlap_end > overlap_start:
                    overlap_len = overlap_end - overlap_start
                    c_len = max(c.anchor_end_idx - c.anchor_start_idx, 1)
                    if overlap_len / c_len > 0.70:
                        overlap = True
                        break
            if not overlap:
                kept.append(c)

        return kept

    def _extract_significant_pivots(self, pivots: List[Pivot], count: int = 6) -> List[Pivot]:
        """From a list of pivots, extracts the `count` most significant ones by price range."""
        if len(pivots) <= count:
            return pivots

        # Score each pivot by how much price changes around it
        scored = []
        for j, p in enumerate(pivots):
            range_before = abs(p.price - pivots[j-1].price) if j > 0 else 0
            range_after = abs(pivots[j+1].price - p.price) if j < len(pivots)-1 else 0
            scored.append((range_before + range_after, j, p))

        # Always keep first and last
        scored.sort(key=lambda x: x[0], reverse=True)
        keep_indices = {0, len(pivots) - 1}
        for _, j, _ in scored:
            if len(keep_indices) >= count:
                break
            keep_indices.add(j)

        selected = [pivots[j] for j in sorted(keep_indices)]
        return selected[:count]

    def _determine_degree_by_duration(self, start_pivot: 'Pivot', end_pivot: 'Pivot') -> str:
        """
        Assigns an Elliott Wave degree based on the CALENDAR duration between two pivots.
        Uses actual dates rather than bar indices to correctly handle non-trading days.
        """
        try:
            delta = (pd.Timestamp(end_pivot.time) - pd.Timestamp(start_pivot.time)).days
        except Exception:
            # Fallback: estimate from bar count (assume ~252 trading days/year)
            delta = int((end_pivot.index - start_pivot.index) * 365 / 252)

        if delta > 730:      # > 2 years
            return "Cycle"
        elif delta > 180:    # > 6 months
            return "Primary"
        elif delta > 45:     # > 6 weeks
            return "Intermediate"
        elif delta > 14:     # > 2 weeks
            return "Minor"
        else:
            return "Minuette"

    def run_analysis(self, min_move_mult: float = 1.0) -> Tuple[List[WaveNode], List[List[WaveNode]]]:
        """Top-Down Elliott Wave Analysis."""
        pivots_t1 = self.run_adaptive_zigzag(min_move_mult)
        if len(pivots_t1) < 2:
            return [], []
            
        # Top-down labeling (find anchor impulse, fill gaps)
        primary_count = self._top_down_label(pivots_t1)
        
        # Subdivide each labeled wave dynamically
        for wave in primary_count:
            self._recursive_subdivide(wave, min_move_mult * 0.4, depth=2)
            
        # Generate an alternate count by strictly viewing it as a correction
        alt_count = self._top_down_label(pivots_t1, force_corrective=True)
        for wave in alt_count:
            self._recursive_subdivide(wave, min_move_mult * 0.4, depth=2)
            
        alternates = [alt_count] if alt_count else []
            
        return primary_count, alternates

    def _top_down_label(self, pivots: List[Pivot], force_corrective: bool = False) -> List[WaveNode]:
        """
        Anchor-based parsing:
        1. Finds the best 5-wave sequence to anchor the chart.
        2. Fills the preceding and succeeding pivots as corrective or connecting waves.
        """
        waves: List[WaveNode] = []
        n = len(pivots)
        
        if n < 6 or force_corrective:
            # Not enough pivots for a motive, or forced corrective. Just sequence 3-wave fallbacks.
            return self._fallback_sequential(pivots, 0, n)
            
        # Find all valid 5-wave motive sequences
        motive_candidates = []
        for i in range(n - 5):
            candidate = pivots[i:i+6]
            is_imp, _ = self.verify_impulse_rules(candidate)
            is_diag, _ = self.verify_diagonal_rules(candidate)
            if is_imp or is_diag:
                score = self.score_impulse(candidate) if is_imp else self.score_diagonal(candidate)
                # Size in price
                size = abs(candidate[-1].price - candidate[0].price)
                motive_candidates.append((score, size, i, candidate, is_diag))
                
        if not motive_candidates:
            return self._fallback_sequential(pivots, 0, n)

        # Add recency bonus: reward structures that end closer to the most recent bar.
        # This stops an old massive wave from always dominating over a fresh recent one.
        total_bars = float(max(pivots[-1].index, 1))
        adjusted = []
        for score, size, i, cand, is_diag in motive_candidates:
            recency_bonus = (cand[-1].index / total_bars) * 3.0
            adjusted.append((score + recency_bonus, size, i, cand, is_diag))

        # Pick the best anchor (highest adjusted score, tie-break by price size)
        adjusted.sort(key=lambda x: (x[0], x[1]), reverse=True)
        best_anchor = adjusted[0]
        score, size, best_i, anchor_pivots, is_diag = best_anchor

        # Determine degree based on actual calendar duration of this anchor
        degree = self._determine_degree_by_duration(anchor_pivots[0], anchor_pivots[-1])
        
        # 1. Fill preceding pivots
        if best_i > 0:
            pre_waves = self._top_down_label(pivots[:best_i+1], force_corrective=force_corrective)
            waves.extend(pre_waves)
            
        # 2. Append the anchor motive
        anchor_waves = self._construct_waves_from_pivots(anchor_pivots, degree, is_diagonal=is_diag)
        waves.extend(anchor_waves)
        
        # 3. Fill succeeding pivots
        end_idx = best_i + 5
        if end_idx < n - 1:
            post_waves = self._top_down_label(pivots[end_idx:], force_corrective=force_corrective)
            waves.extend(post_waves)
            
        return waves

    def _fallback_sequential(self, pivots: List[Pivot], offset: int, length: int, degree: str = None) -> List[WaveNode]:
        """Fills gaps with 3-wave ABC structures or single connecting waves."""
        waves = []
        if length < 2:
            return waves
            
        # Determine degree if not passed
        if not degree:
            degree = self._determine_degree_by_duration(pivots[0], pivots[-1])
            
        i = 0
        while i < length - 1:
            rem = length - 1 - i
            
            if rem >= 3:
                candidate = pivots[i:i+4]
                # Check zigzag or flat
                is_zz, _ = self.verify_zigzag_rules(candidate)
                is_fl, _ = self.verify_flat_rules(candidate)
                if is_zz or is_fl:
                    sub_waves = self._construct_corrective_fallback(candidate, degree)
                    waves.extend(sub_waves)
                    i += 3
                    continue
                    
            # Fallback segment
            start = pivots[i]
            end = pivots[i+1]
            labels = self.DEGREE_LABELS[degree]["corrective"]
            label_idx = i % len(labels)
            label = labels[label_idx]
            waves.append(WaveNode(start, end, label, degree, wave_type="corrective"))
            i += 1
            
        return waves

    def _get_pivot_vals(self, pivots: List[Pivot]) -> List[float]:
        return [p.log_price if self.use_log_scale else p.price for p in pivots]

    def _get_atr_buffer(self, pivot: Pivot, multiplier: float = 0.3) -> float:
        atr = float(self.df['ATR'].iloc[pivot.index])
        if self.use_log_scale:
            close = float(self.df['Close'].iloc[pivot.index])
            return multiplier * (atr / close)
        return multiplier * atr

    def verify_impulse_rules(self, pivots: List[Pivot]) -> Tuple[bool, List[Dict[str, Any]]]:
        """Strict structural checks for 5-wave Impulse with Noise Tolerance."""
        checklist = []
        if len(pivots) < 6:
            return False, []
            
        v = self._get_pivot_vals(pivots)
        w1, w2, w3, w4, w5 = v[1]-v[0], v[2]-v[1], v[3]-v[2], v[4]-v[3], v[5]-v[4]
        is_uptrend = w1 > 0
        
        # 0. Check alternating direction
        direction_ok = True
        if is_uptrend:
            direction_ok = (w1 > 0 and w2 < 0 and w3 > 0 and w4 < 0 and w5 > 0)
        else:
            direction_ok = (w1 < 0 and w2 > 0 and w3 < 0 and w4 > 0 and w5 < 0)
            
        checklist.append({"rule": "Alternating Directions", "status": direction_ok})
        if not direction_ok:
            return False, checklist
            
        # STRICT: No ATR buffer tolerance on cardinal rules
            
        # 1. W2 retracement < 100% of W1 (with noise tolerance)
        w2_retrace_ok = v[2] > v[0] if is_uptrend else v[2] < v[0]
        checklist.append({"rule": "W2 Retracement < 100% W1", "status": w2_retrace_ok})
        
        # 2. W3 not the shortest (price)
        w3_not_shortest = abs(w3) >= min(abs(w1), abs(w5))
        checklist.append({"rule": "W3 Not Shortest Price", "status": w3_not_shortest})
        
        # 3. W4 no overlap with W1 territory (with noise tolerance)
        w4_no_overlap = v[4] > v[1] if is_uptrend else v[4] < v[1]
        checklist.append({"rule": "W4-W1 No Overlap", "status": w4_no_overlap})
        
        # W3 time ratio removed — not a cardinal Elliott Wave rule
        
        # 4b. Time Fibs - Wave 2 duration shouldn't exceed 5x Wave 1
        t1 = pivots[1].index - pivots[0].index
        t2 = pivots[2].index - pivots[1].index
        w2_time_ok = t2 <= 5 * max(1, t1)
        checklist.append({"rule": "W2 Duration <= 5x W1 (Time Stop)", "status": w2_time_ok})
        
        # 5. W5 at least 38.2% of W4
        w5_length_ok = abs(w5) >= 0.382 * abs(w4)
        checklist.append({"rule": "W5 >= 38.2% of W4 (Guideline)", "status": w5_length_ok})
        
        # Only strict rules invalidate the structure
        all_passed = w2_retrace_ok and w3_not_shortest and w4_no_overlap
        return all_passed, checklist

    def verify_diagonal_rules(self, pivots: List[Pivot]) -> Tuple[bool, List[Dict[str, Any]]]:
        """Strict structural checks for 5-wave Diagonal Triangle with Tolerance."""
        checklist = []
        if len(pivots) < 6:
            return False, []
            
        v = self._get_pivot_vals(pivots)
        w1, w2, w3, w4, w5 = v[1]-v[0], v[2]-v[1], v[3]-v[2], v[4]-v[3], v[5]-v[4]
        is_uptrend = w1 > 0
        
        direction_ok = (w1 > 0 and w2 < 0 and w3 > 0 and w4 < 0 and w5 > 0) if is_uptrend else (w1 < 0 and w2 > 0 and w3 < 0 and w4 > 0 and w5 < 0)
        checklist.append({"rule": "Alternating Directions", "status": direction_ok})
        if not direction_ok:
            return False, checklist

        buffer = self._get_atr_buffer(pivots[0])

        # 1. W2 retracement < 100% of W1
        w2_retrace_ok = v[2] > (v[0] - buffer) if is_uptrend else v[2] < (v[0] + buffer)
        checklist.append({"rule": "W2 Retracement < 100% W1", "status": w2_retrace_ok})
        
        # 2. W4 MUST overlap W1 territory
        w4_overlap_ok = v[4] <= v[1] if is_uptrend else v[4] >= v[1]
        w4_not_exceed_w3 = v[4] > v[2] if is_uptrend else v[4] < v[2]
        w4_overlap_valid = w4_overlap_ok and w4_not_exceed_w3
        checklist.append({"rule": "W4 Overlaps W1 but stays within W3 bounds", "status": w4_overlap_valid})
        
        # 3. W5 shorter than W3 (often true in contracting, relaxed for expanding)
        w5_shorter_w3 = abs(w5) < abs(w3) * 1.15
        checklist.append({"rule": "W5 Shorter than W3 (relaxed)", "status": w5_shorter_w3})
        
        # 4. Trendline convergence/divergence
        dist_3 = abs(v[3] - v[2])
        dist_5 = abs(v[5] - v[4])
        trendlines_converge = (dist_5 < dist_3) or (dist_5 > 1.10 * dist_3)
        checklist.append({"rule": "Trendline Convergence/Divergence (Guideline)", "status": trendlines_converge})
        
        all_passed = w2_retrace_ok and w4_overlap_valid
        return all_passed, checklist

    def verify_zigzag_rules(self, pivots: List[Pivot]) -> Tuple[bool, List[Dict[str, Any]]]:
        """Zigzag correction rules (A-B-C) with noise tolerance."""
        checklist = []
        if len(pivots) < 4:
            return False, []
            
        v = self._get_pivot_vals(pivots)
        wA, wB, wC = v[1]-v[0], v[2]-v[1], v[3]-v[2]
        is_uptrend = wA > 0
        
        direction_ok = (wA > 0 and wB < 0 and wC > 0) if is_uptrend else (wA < 0 and wB > 0 and wC < 0)
        checklist.append({"rule": "A-B-C Directions", "status": direction_ok})
        if not direction_ok:
            return False, checklist

        buffer = self._get_atr_buffer(pivots[0])

        # 1. B < 100% of A
        b_retrace_ok = v[2] > (v[0] - buffer) if is_uptrend else v[2] < (v[0] + buffer)
        checklist.append({"rule": "B Retrace < 100% of A", "status": b_retrace_ok})
        
        # 2. C ends beyond A's end (Guideline)
        c_beyond_a = v[3] > (v[1] - buffer) if is_uptrend else v[3] < (v[1] + buffer)
        checklist.append({"rule": "C Ends Beyond A (Guideline)", "status": c_beyond_a})
        
        # Only strict structural rules cause hard-fails
        all_passed = b_retrace_ok
        return all_passed, checklist

    def verify_flat_rules(self, pivots: List[Pivot]) -> Tuple[bool, List[Dict[str, Any]]]:
        """Flat correction rules (3-3-5)."""
        checklist = []
        if len(pivots) < 4:
            return False, []
            
        v = self._get_pivot_vals(pivots)
        wA, wB, wC = v[1]-v[0], v[2]-v[1], v[3]-v[2]
        is_uptrend = wA > 0
        
        direction_ok = (wA > 0 and wB < 0 and wC > 0) if is_uptrend else (wA < 0 and wB > 0 and wC < 0)
        checklist.append({"rule": "A-B-C Directions", "status": direction_ok})
        if not direction_ok:
            return False, checklist

        # 1. B retraces at least 80% of A (relaxed from 90%)
        b_retrace_80 = abs(wB) >= 0.80 * abs(wA)
        checklist.append({"rule": "B Retraces >= 80% of A", "status": b_retrace_80})
        
        all_passed = all(item["status"] for item in checklist)
        return all_passed, checklist

    def score_impulse(self, pivots: List[Pivot]) -> float:
        """Scores an Impulse wave pattern using Fibonacci and channel conformance."""
        score = 0.0
        v = self._get_pivot_vals(pivots)
        w1, w2, w3, w4, w5 = v[1]-v[0], v[2]-v[1], v[3]-v[2], v[4]-v[3], v[5]-v[4]

        r2 = abs(w2) / abs(w1) if abs(w1) > 0 else 0
        if 0.50 <= r2 <= 0.786:
            score += 1.0
        elif 0.382 <= r2 < 0.50:
            score += 0.5  # shallow but acceptable

        r3 = abs(w3) / abs(w1) if abs(w1) > 0 else 0
        if 2.0 <= r3 <= 2.618:
            score += 4.0   # Extended third — the most powerful EW setup
        elif 1.618 <= r3 < 2.0:
            score += 2.0   # Classic W3 extension
        elif r3 >= 1.0:
            score += 0.5

        r4 = abs(w4) / abs(w3) if abs(w3) > 0 else 0
        if 0.236 <= r4 <= 0.382:
            score += 1.0
        elif 0.382 < r4 <= 0.50:
            score += 0.5

        w13_length = abs(v[3] - v[0])
        r5 = abs(w5) / w13_length if w13_length > 0 else 0
        if 0.618 <= r5 <= 1.0:
            score += 1.0
        elif 0.382 <= r5 < 0.618:
            score += 0.5

        # Alternation bonus: W2 and W4 should alternate in character
        if (r2 > 0.50 and r4 < 0.382) or (r2 < 0.382 and r4 > 0.50):
            score += 3.0

        # Channel conformance: W5 should end near the upper/lower channel line
        idx1, idx2, idx3, idx5 = pivots[1].index, pivots[2].index, pivots[3].index, pivots[5].index
        t_span_13 = idx3 - idx1
        if t_span_13 > 0:
            slope = (v[3] - v[1]) / t_span_13
            proj_y = v[2] + slope * (idx5 - idx2)
            diff = abs(v[5] - proj_y) / abs(v[5]) if v[5] != 0 else 0
            if diff <= 0.03:
                score += 2.5  # Very tight channel adherence
            elif diff <= 0.07:
                score += 1.0

        # RSI Momentum & Divergence Check
        if 'RSI' in self.df.columns:
            try:
                rsi_3 = self.df['RSI'].iloc[pivots[3].index]
                rsi_5 = self.df['RSI'].iloc[pivots[5].index]
                if not pd.isna(rsi_3) and not pd.isna(rsi_5):
                    is_uptrend = v[1] > v[0]
                    if is_uptrend:
                        if v[5] > v[3] and rsi_5 < rsi_3:
                            score += 3.0  # Bearish RSI divergence on W5 = textbook exhaustion
                        if rsi_3 > 70:
                            score += 1.0  # High RSI momentum on W3
                    else:
                        if v[5] < v[3] and rsi_5 > rsi_3:
                            score += 3.0
                        if rsi_3 < 30:
                            score += 1.0
            except (IndexError, KeyError):
                pass

        return score

    def score_diagonal(self, pivots: List[Pivot]) -> float:
        score = 1.0
        v = self._get_pivot_vals(pivots)
        w3, w1 = v[3]-v[2], v[1]-v[0]
        r3 = abs(w3) / abs(w1) if abs(w1) > 0 else 0
        if 0.618 <= r3 <= 1.618:
            score += 1.5
        return score

    def _construct_waves_from_pivots(self, pivots: List[Pivot], degree: str, is_diagonal: bool = False) -> List[WaveNode]:
        waves: List[WaveNode] = []
        labels = self.DEGREE_LABELS[degree]["motive"] if not is_diagonal else self.DEGREE_LABELS[degree]["diagonal"]
        w_type = "motive" if not is_diagonal else "corrective"
        
        score = self.score_impulse(pivots) if not is_diagonal else self.score_diagonal(pivots)
        
        for k in range(5):
            start = pivots[k]
            end = pivots[k+1]
            label = labels[k]
            wave = WaveNode(start, end, label, degree, wave_type=w_type)
            wave.score = score
            
            if k == 1: 
                wave.fib_levels = self._calc_fib_retracement_levels(pivots[0], pivots[1])
                wave.invalidation_price = pivots[0].price
                t1 = pivots[1].index - pivots[0].index
                t2 = pivots[2].index - pivots[1].index
                if t2 > 5 * max(1, t1):
                    wave.time_invalidated = True
            elif k == 3: 
                wave.fib_levels = self._calc_fib_retracement_levels(pivots[2], pivots[3])
                wave.invalidation_price = pivots[1].price 
            elif k == 4:
                is_uptrend = pivots[1].price > pivots[0].price
                if is_uptrend and end.price < pivots[3].price:
                    wave.is_truncated = True
                elif not is_uptrend and end.price > pivots[3].price:
                    wave.is_truncated = True
                
            waves.append(wave)
        return waves

    def _construct_corrective_fallback(self, pivots: List[Pivot], degree: str) -> List[WaveNode]:
        waves: List[WaveNode] = []
        labels = self.DEGREE_LABELS[degree]["corrective"]
        
        count = min(3, len(pivots)-1)
        for k in range(count):
            start = pivots[k]
            end = pivots[k+1]
            label = labels[k] if k < len(labels) else f"C_alt_{k}"
            wave = WaveNode(start, end, label, degree, wave_type="corrective")
            waves.append(wave)
            
        return waves

    def _calc_fib_retracement_levels(self, start: Pivot, end: Pivot) -> Dict[str, float]:
        p_start = start.price
        p_end = end.price
        diff = p_end - p_start
        
        ratios = [0.236, 0.382, 0.5, 0.618, 0.786]
        levels = {}
        for r in ratios:
            if self.use_log_scale:
                l_start = start.log_price
                l_end = end.log_price
                l_diff = l_end - l_start
                val = np.exp(l_end - r * l_diff)
            else:
                val = p_end - r * diff
            levels[f"{r:.3f}"] = float(val)
            
        return levels

    def _recursive_subdivide(self, parent_wave: WaveNode, default_min_move: float, depth: int):
        """
        Dynamically finds sub-waves by localizing the ZigZag search to the parent's date range.
        This guarantees we find sub-fractals even in highly volatile short-duration parent waves.
        """
        parent_degree_idx = self.DEGREE_ORDER.index(parent_wave.degree)
        if parent_degree_idx >= len(self.DEGREE_ORDER) - 1:
            return 
            
        child_degree = self.DEGREE_ORDER[parent_degree_idx + 1]
        
        # Dynamic localization
        start_idx = parent_wave.start_pivot.index
        end_idx = parent_wave.end_pivot.index
        
        # If parent duration is too small, fallback
        if end_idx - start_idx < 4:
            return
            
        # We need a dynamic threshold proportional to the parent wave's range
        # Average parent percentage move
        parent_range_pct = abs(parent_wave.end_pivot.price - parent_wave.start_pivot.price) / parent_wave.start_pivot.price
        # Aim for sub-swings that are roughly 15-25% of the parent wave size
        dynamic_move_mult = max(0.1, (parent_range_pct * 0.20) / self.df['min_move_pct'].iloc[start_idx:end_idx].mean())
        
        # Run ZigZag locally
        sub_pivots = self.run_adaptive_zigzag(min_move_mult=dynamic_move_mult, start_idx=start_idx, end_idx=end_idx)
        
        if len(sub_pivots) < 4:
            # Fallback to default
            sub_pivots = self.run_adaptive_zigzag(min_move_mult=default_min_move, start_idx=start_idx, end_idx=end_idx)
            
        if len(sub_pivots) < 4:
            return
            
        sub_waves: List[WaveNode] = []
        
        if parent_wave.wave_type == "motive":
            if len(sub_pivots) >= 6:
                slice_pivs = sub_pivots[:6]
                is_imp, check_imp = self.verify_impulse_rules(slice_pivs)
                if is_imp:
                    sub_waves = self._construct_waves_from_pivots(slice_pivs, child_degree)
                else:
                    is_diag, check_diag = self.verify_diagonal_rules(slice_pivs)
                    if is_diag:
                        sub_waves = self._construct_waves_from_pivots(slice_pivs, child_degree, is_diagonal=True)
        elif parent_wave.wave_type == "corrective":
            if len(sub_pivots) >= 4:
                slice_pivs = sub_pivots[:4]
                is_zz, check_zz = self.verify_zigzag_rules(slice_pivs)
                if is_zz:
                    sub_waves = self._construct_corrective_fallback(slice_pivs, child_degree)
                else:
                    is_fl, check_fl = self.verify_flat_rules(slice_pivs)
                    if is_fl:
                        sub_waves = self._construct_corrective_fallback(slice_pivs, child_degree)

        if sub_waves:
            consistent = True
            parent_duration = parent_wave.get_duration()
            parent_range = parent_wave.get_price_range(self.use_log_scale)
            
            for sw in sub_waves:
                if sw.get_duration() >= 0.95 * parent_duration:
                    consistent = False
                    break
                if sw.get_price_range(self.use_log_scale) >= parent_range * 1.05:
                    consistent = False
                    break
                    
            if consistent:
                parent_wave.sub_waves = sub_waves
                for sw in sub_waves:
                    self._recursive_subdivide(sw, default_min_move * 0.5, depth - 1)

    def get_trade_recommendation(self, last_block: List[WaveNode]) -> Dict[str, Any]:
        """Generates a trade recommendation based on the current active wave block."""
        n = len(last_block)
        if n == 0:
            return {"bias": "Neutral", "reason": "No clear wave structure detected.", "target": None, "invalidation": None}
            
        last_wave = last_block[-1]
        is_uptrend = last_wave.end_pivot.price > last_wave.start_pivot.price
        lbl = last_wave.label
        
        bias = "Neutral"
        reason = ""
        target = None
        inval = last_wave.invalidation_price
        
        if lbl in ["[1]", "(1)", "1", "{1}", "i"]:
            bias = "Bearish (Short-term)" if is_uptrend else "Bullish (Short-term)"
            reason = "Wave 1 complete. High-probability entry on the upcoming Wave 2 retracement."
            diff = last_wave.end_pivot.price - last_wave.start_pivot.price
            target = last_wave.end_pivot.price - (0.618 * diff)
            
        elif lbl in ["[2]", "(2)", "2", "{2}", "ii"]:
            primary_bullish = not is_uptrend 
            bias = "Bullish" if primary_bullish else "Bearish"
            reason = "Wave 2 complete. Premium A+ setup for Wave 3 extension."
            if n >= 2:
                w1 = last_block[-2]
                w1_diff = w1.end_pivot.price - w1.start_pivot.price
                target = last_wave.end_pivot.price + (1.618 * w1_diff)
                
        elif lbl in ["[3]", "(3)", "3", "{3}", "iii"]:
            primary_bullish = is_uptrend
            bias = "Bearish (Short-term)" if primary_bullish else "Bullish (Short-term)"
            reason = "Wave 3 complete. Anticipating sideways/shallow Wave 4 correction."
            w3_diff = last_wave.end_pivot.price - last_wave.start_pivot.price
            target = last_wave.end_pivot.price - (0.382 * w3_diff)
                
        elif lbl in ["[4]", "(4)", "4", "{4}", "iv"]:
            primary_bullish = not is_uptrend
            bias = "Bullish" if primary_bullish else "Bearish"
            reason = "Wave 4 complete. Final Wave 5 thrust expected."
            if n >= 4:
                w1 = last_block[-4]
                w3 = last_block[-2]
                net_13 = w3.end_pivot.price - w1.start_pivot.price
                target = last_wave.end_pivot.price + (0.618 * net_13)
                
        elif lbl in ["[5]", "(5)", "5", "{5}", "v"]:
            primary_bullish = is_uptrend
            bias = "Bearish (Correction)" if primary_bullish else "Bullish (Correction)"
            reason = "Wave 5 complete. Exhaustion phase. Stop-and-reverse for macro correction."
            diff = last_wave.end_pivot.price - last_block[0].start_pivot.price
            target = last_wave.end_pivot.price - (0.382 * diff)
            
        elif lbl in ["[A]", "(A)", "A", "{A}", "a"]:
            bias = "Bullish (Short-term)" if not is_uptrend else "Bearish (Short-term)"
            reason = "Wave A complete. Expecting a Wave B bounce."
            diff = last_wave.end_pivot.price - last_wave.start_pivot.price
            target = last_wave.end_pivot.price - (0.5 * diff)
            
        elif lbl in ["[B]", "(B)", "B", "{B}", "b"]:
            primary_bearish = not is_uptrend
            bias = "Bearish" if primary_bearish else "Bullish"
            reason = "Wave B complete. Expecting impulsive Wave C."
            if n >= 2:
                wa = last_block[-2]
                wa_diff = wa.end_pivot.price - wa.start_pivot.price
                target = last_wave.end_pivot.price + (1.0 * wa_diff)
                
        elif lbl in ["[C]", "(C)", "C", "{C}", "c"]:
            primary_bullish = not is_uptrend
            bias = "Bullish (Reversal)" if primary_bullish else "Bearish (Reversal)"
            reason = "Correction (A-B-C) complete. Expecting new motive wave in primary direction."
            
        return {
            "bias": bias,
            "reason": reason,
            "target": target,
            "invalidation": inval,
            "current_price": float(self.df['Close'].iloc[-1])
        }

    def _find_last_wave_block(self, waves: List[WaveNode]) -> List[WaveNode]:
        if not waves:
            return []
        last_label = waves[-1].label
        if last_label in ["[5]", "(5)", "5", "{5}", "v"]:
            return waves[-5:] if len(waves) >= 5 else waves
        elif last_label in ["[C]", "(C)", "C", "{C}", "c"]:
            return waves[-3:] if len(waves) >= 3 else waves
        else:
            degree = waves[-1].degree
            degree_waves = [w for w in waves if w.degree == degree]
            if len(degree_waves) >= 5:
                if degree_waves[-1].label in ["[5]", "(5)", "5", "{5}", "v"] or degree_waves[-5].label in ["[1]", "(1)", "1", "{1}", "i"]:
                    return degree_waves[-5:]
            if len(degree_waves) >= 3:
                return degree_waves[-3:]
            return degree_waves

    def get_summary_engine_payload(self, primary_waves: List[WaveNode], alternate_waves: List[List[WaveNode]]) -> Dict[str, Any]:
        def build_count_data(waves: List[WaveNode], is_alt: bool = False):
            if not waves:
                return None
            last_block = self._find_last_wave_block(waves)
            if not last_block:
                return None
                
            rec = self.get_trade_recommendation(last_block)
            last_wave = last_block[-1]
            scenario = f"Wave {last_wave.label} of {last_wave.wave_type.capitalize()} Phase"
            larger_context = f"Wave {last_wave.label} of {last_wave.degree}"
            trend = rec["bias"]
            
            pivs = [last_block[0].start_pivot] + [w.end_pivot for w in last_block]
            
            # Confidence Score & Guidelines
            guidelines = []
            score = 1.0
            
            if len(last_block) == 5:
                score = self.score_impulse(pivs)
                # Check momentum confluence
                if 'MACD_Hist' in self.df.columns and not pd.isna(self.df['MACD_Hist'].iloc[pivs[-1].index]):
                    macd_val = self.df['MACD_Hist'].iloc[pivs[-1].index]
                    if (trend == "Bullish" and macd_val > 0) or (trend == "Bearish" and macd_val < 0):
                        score += 1.5
                        guidelines.append("MACD Momentum Confluence")
                
                is_valid, checklist = self.verify_impulse_rules(pivs)
                for item in checklist:
                    if item["status"] and not item["rule"].startswith("W2"):
                        # Keep guidelines brief
                        guidelines.append(item["rule"])
                
                # Check Alternation specifically
                v = self._get_pivot_vals(pivs)
                w2, w4, w1, w3 = abs(v[2]-v[1]), abs(v[4]-v[3]), abs(v[1]-v[0]), abs(v[3]-v[2])
                r2 = w2/w1 if w1 > 0 else 0
                r4 = w4/w3 if w3 > 0 else 0
                if (r2 > 0.50 and r4 < 0.382) or (r2 < 0.382 and r4 > 0.50):
                    score += 1.0
                    guidelines.append("W2/W4 Alternation")
                    
            elif len(last_block) >= 3:
                is_zz, zz_check = self.verify_zigzag_rules(pivs[:4])
                is_flat, flat_check = self.verify_flat_rules(pivs[:4])
                if is_flat and not is_zz:
                    score = 4.0
                    checklist = flat_check
                elif is_zz:
                    score = 5.0
                    checklist = zz_check
                else:
                    score = 2.0
                    checklist = zz_check
                    
                for item in checklist:
                    if item["status"]:
                        guidelines.append(item["rule"])
            
            actionable = {}
            target = rec["target"]
            inval = rec["invalidation"]
            curr = rec["current_price"]
            
            if target is not None:
                actionable["target_price"] = round(target, 2)
            if inval is not None:
                actionable["invalidation_level"] = round(inval, 2)
            if target is not None and inval is not None:
                risk = abs(curr - inval)
                reward = abs(target - curr)
                if risk > 0:
                    actionable["risk_reward_ratio"] = round(reward / risk, 2)
                    
            recent_waves = [{"label": w.label, "tier_price": round(w.end_pivot.price, 2)} for w in waves[-4:]]
                    
            res = {
                "waves": waves,
                "is_alternate": is_alt,
                "scenario": scenario,
                "larger_context": larger_context,
                "trend": trend,
                "raw_score": score,
                "guidelines_met": guidelines,
                "recent_waves": recent_waves,
                "actionable": actionable
            }
            return res

        p_data = build_count_data(primary_waves, is_alt=False)
        a_data = build_count_data(alternate_waves[0] if alternate_waves else [], is_alt=True)
        
        # Normalize Probabilities (Max 95%)
        p_score = p_data["raw_score"] if p_data else 0.0
        a_score = a_data["raw_score"] if a_data else 0.0
        
        # Swap logic if Alternate structurally scores higher than Primary!
        if a_data and p_data and a_score > p_score:
            p_data, a_data = a_data, p_data
            p_score, a_score = a_score, p_score
            
        total_score = p_score + a_score
        if total_score == 0:
            total_score = 1
            
        if p_data:
            p_prob = min(0.95, p_score / max(total_score, 10.0))
            if not a_data:
                p_prob = min(0.95, p_score / 10.0)
            p_data["confidence_score"] = round(p_prob, 2)
            
        if a_data:
            a_prob = min(0.95 - p_data["confidence_score"], a_score / max(total_score, 10.0))
            if a_prob < 0.01:
                a_prob = 0.01
            a_data["confidence_score"] = round(a_prob, 2)

        payload = {
            "summary": {
                "current_degree": primary_waves[-1].degree if primary_waves else "Unknown",
                "primary_count": p_data,
                "alternate_count": a_data
            }
        }
        return payload

    def calculate_enhanced_stats(self, primary_waves: List[WaveNode], alternate_waves: List[List[WaveNode]], trade_rec: Dict[str, Any] = None) -> Dict[str, Any]:
        """Calculates rich structural statistics: Phase, Progress %, Fib Harmony Score, ATR Context, Momentum."""
        if not primary_waves:
            return {
                "phase": "Undetected",
                "progress_pct": 0.0,
                "fib_harmony_score": 50,
                "harmony_rating": "Standard",
                "atr_val": 0.0,
                "atr_pct": 0.0,
                "atr_context": "Normal Volatility",
                "momentum_status": "Neutral"
            }
            
        last_wave = primary_waves[-1]
        phase = f"{last_wave.wave_type.capitalize()} Phase: Wave {last_wave.label} of {last_wave.degree}"
        
        # Calculate wave progress % based on price amplitude relative to starting price
        start_p = primary_waves[0].start_pivot.price
        curr_p = last_wave.end_pivot.price
        total_span = abs(curr_p - start_p)
        wave_span = abs(last_wave.end_pivot.price - last_wave.start_pivot.price)
        progress_pct = min(100.0, round((wave_span / max(total_span, 1.0)) * 100.0, 1)) if total_span > 0 else 50.0

        # Calculate Fib Harmony Score
        scores = [w.score for w in primary_waves if w.score > 0]
        avg_score = np.mean(scores) if scores else 5.0
        harmony_score = min(98, max(45, int((avg_score / 12.0) * 100)))
        if harmony_score >= 85:
            harmony_rating = "Exceptional Harmony"
        elif harmony_score >= 70:
            harmony_rating = "Strong Alignment"
        else:
            harmony_rating = "Standard Alignment"

        # Calculate Volatility & ATR Context
        close_p = self.df['Close'].iloc[-1]
        if 'ATR' in self.df.columns and not pd.isna(self.df['ATR'].iloc[-1]):
            atr_val = float(self.df['ATR'].iloc[-1])
        else:
            # Simple ATR estimation from High - Low
            atr_val = float((self.df['High'] - self.df['Low']).tail(14).mean())
        
        atr_pct = round((atr_val / max(close_p, 0.01)) * 100.0, 2)
        if atr_pct > 3.0:
            atr_context = "High Volatility"
        elif atr_pct < 1.0:
            atr_context = "Low Volatility"
        else:
            atr_context = "Normal Volatility"

        # Calculate Momentum Status (Harmonized with Setup Bias to prevent contradictions)
        bias = trade_rec.get("bias", "") if trade_rec else ""
        if "Bullish" in bias:
            momentum_status = "🟢 Bullish Setup Confirmed"
        elif "Bearish" in bias:
            momentum_status = "🔴 Bearish Setup Confirmed"
        else:
            momentum_status = "🟡 Neutral / Consolidating"

        if 'RSI' in self.df.columns and not pd.isna(self.df['RSI'].iloc[-1]):
            rsi = self.df['RSI'].iloc[-1]
            if rsi > 70:
                momentum_status += " (RSI Overbought)"
            elif rsi < 30:
                momentum_status += " (RSI Oversold)"

        return {
            "phase": phase,
            "progress_pct": progress_pct,
            "fib_harmony_score": harmony_score,
            "harmony_rating": harmony_rating,
            "atr_val": round(atr_val, 2),
            "atr_pct": atr_pct,
            "atr_context": atr_context,
            "momentum_status": momentum_status
        }

    def generate_tactical_tips(self, last_block: List[WaveNode], trade_rec: Dict[str, Any]) -> Dict[str, Any]:
        """Generates dynamic execution and pattern strategy tips based on current setup."""
        if not last_block or not trade_rec:
            return {
                "entry_tip": "Wait for a confirmed pivot structure before executing entries.",
                "stop_tip": "Always maintain strict invalidation discipline.",
                "exit_tip": "Target Fibonacci extensions for systematic profit scaling.",
                "pattern_rules": ["Ensure 5-wave motive and 3-wave corrective compliance."]
            }
            
        last_wave = last_block[-1]
        lbl = last_wave.label
        target = trade_rec.get("target")
        inval = trade_rec.get("invalidation")
        curr = trade_rec.get("current_price", self.df['Close'].iloc[-1])
        
        entry_tip = f"Look for confirmation around current level ({curr:,.2f}) with daily volume expansion."
        if target:
            if curr < target:
                entry_tip = f"Bullish setup: Consider entry in zone {curr:,.2f}–{curr*1.005:,.2f} targeting {target:,.2f}."
            else:
                entry_tip = f"Bearish retrace setup: Consider short entry near {curr:,.2f} targeting lower support at {target:,.2f}."

        stop_tip = "Keep invalidation tight to structural pivot bounds."
        if inval:
            stop_tip = f"Place hard stop loss at invalidation level {inval:,.2f}. Trail stop to breakeven once price moves 50% toward target."

        exit_tip = "Scale out position at primary target; hold remainder for higher degree extension."
        if target:
            exit_tip = f"Primary target set at {target:,.2f}. Scale out profits incrementally as price approaches target."

        pattern_rules = []
        if lbl in ["[1]", "(1)", "1", "{1}", "i"]:
            pattern_rules = [
                "Wave 1 Confirmation: Ensure initial impulse broke out of the prior corrective channel.",
                "Upcoming Wave 2: Expect a deep retracement (50% to 78.6% of W1). Prepare entry orders."
            ]
        elif lbl in ["[2]", "(2)", "2", "{2}", "ii"]:
            pattern_rules = [
                "Wave 2 Entry: Premium A+ setup. Invalidation is fixed at the start of Wave 1.",
                "Wave 3 Expectation: Wave 3 is usually the longest and most powerful. Target 1.618x W1 extension."
            ]
        elif lbl in ["[3]", "(3)", "3", "{3}", "iii"]:
            pattern_rules = [
                "Wave 3 Rule: Wave 3 can NEVER be the shortest wave among 1, 3, and 5.",
                "Wave 4 Preparation: Wave 4 cannot overlap Wave 1 price territory. Expect shallow 23.6–38.2% retrace."
            ]
        elif lbl in ["[4]", "(4)", "4", "{4}", "iv"]:
            pattern_rules = [
                "Wave 4 Rule: Wave 4 MUST NOT enter Wave 1 price zone (Overlap Rule).",
                "Alternation Guideline: If Wave 2 was a sharp zigzag, expect Wave 4 to be a flat/complex sideways retrace."
            ]
        elif lbl in ["[5]", "(5)", "5", "{5}", "v"]:
            pattern_rules = [
                "Wave 5 Exhaustion: Look for RSI/MACD momentum divergence between Wave 3 and Wave 5 peaks.",
                "Macro Reversal: Prepare to take full profits as a major 3-wave correction (A-B-C) follows Wave 5."
            ]
        else:
            pattern_rules = [
                "Corrective Structure: A-B-C corrections retrace previous impulse phases.",
                "Wave C Projection: Wave C typically equals Wave A in length ($C = A$). Watch equality target."
            ]

        return {
            "entry_tip": entry_tip,
            "stop_tip": stop_tip,
            "exit_tip": exit_tip,
            "pattern_rules": pattern_rules
        }

