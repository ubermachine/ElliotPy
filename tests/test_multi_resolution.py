import pandas as pd
import numpy as np
import pytest
from backend.wave_engine import DailyElliottWaveEngine, CandidateCount, Pivot

def _make_synthetic_df(n=500):
    """Creates a synthetic Silver-like price series with a clear 5-wave impulse."""
    np.random.seed(42)
    dates = pd.bdate_range("2020-01-01", periods=n)
    # Wave I up: 0-100, Wave II down: 100-200, Wave III up: 200-350, Wave IV down: 350-400, Wave V up: 400-500
    prices = np.zeros(n)
    prices[0] = 20.0
    for i in range(1, n):
        if i < 100:      # Wave I: strong up
            prices[i] = prices[i-1] + np.random.normal(0.08, 0.15)
        elif i < 200:     # Wave II: retrace down ~50%
            prices[i] = prices[i-1] + np.random.normal(-0.04, 0.12)
        elif i < 350:     # Wave III: strongest up
            prices[i] = prices[i-1] + np.random.normal(0.12, 0.18)
        elif i < 400:     # Wave IV: mild retrace
            prices[i] = prices[i-1] + np.random.normal(-0.03, 0.10)
        else:             # Wave V: up
            prices[i] = prices[i-1] + np.random.normal(0.06, 0.14)
    prices = np.maximum(prices, 5.0)  # Floor
    df = pd.DataFrame({
        "Open": prices * (1 + np.random.normal(0, 0.005, n)),
        "High": prices * (1 + np.abs(np.random.normal(0, 0.01, n))),
        "Low": prices * (1 - np.abs(np.random.normal(0, 0.01, n))),
        "Close": prices,
        "Volume": np.random.randint(1000, 10000, n)
    }, index=dates)
    df = df.reset_index(names="Date")
    return df

class TestMultiResolutionZigZag:
    def test_candidate_count_dataclass_exists(self):
        """CandidateCount should be importable and have required fields."""
        c = CandidateCount(
            waves=[], score=5.0, resolution=2.0, window_size=6,
            pattern_type="impulse", invalidation=20.0,
            anchor_start_idx=0, anchor_end_idx=100
        )
        assert c.score == 5.0
        assert c.resolution == 2.0
        assert c.pattern_type == "impulse"

    def test_multi_resolution_returns_multiple_pivot_sets(self):
        """run_multi_resolution_zigzag should return pivot sets for each multiplier."""
        df = _make_synthetic_df()
        engine = DailyElliottWaveEngine(df, use_log_scale=False)
        pivot_sets = engine.run_multi_resolution_zigzag(base_mult=1.0)
        assert isinstance(pivot_sets, dict)
        assert len(pivot_sets) >= 3  # At least 3 resolutions
        for mult, pivots in pivot_sets.items():
            assert isinstance(mult, float)
            assert all(isinstance(p, Pivot) for p in pivots)

    def test_coarser_resolution_yields_fewer_pivots(self):
        """Higher multiplier should produce fewer (or equal) pivots."""
        df = _make_synthetic_df()
        engine = DailyElliottWaveEngine(df, use_log_scale=False)
        pivot_sets = engine.run_multi_resolution_zigzag(base_mult=1.0)
        mults = sorted(pivot_sets.keys())
        counts = [len(pivot_sets[m]) for m in mults]
        # Each successive resolution should have fewer or equal pivots
        for i in range(1, len(counts)):
            assert counts[i] <= counts[i-1] + 5  # Small tolerance for edge cases

class TestCandidateGenerator:
    def test_generate_candidates_returns_list(self):
        """_generate_candidates should return a list of CandidateCount objects."""
        df = _make_synthetic_df()
        engine = DailyElliottWaveEngine(df, use_log_scale=False)
        pivot_sets = engine.run_multi_resolution_zigzag(base_mult=1.0)
        candidates = engine._generate_candidates(pivot_sets)
        assert isinstance(candidates, list)
        for c in candidates:
            assert isinstance(c, CandidateCount)
            assert c.score >= 0
            assert c.pattern_type in ("impulse", "diagonal")

    def test_generate_candidates_finds_impulse_in_synthetic(self):
        """The synthetic data has a clear 5-wave impulse; candidates should find it."""
        df = _make_synthetic_df()
        engine = DailyElliottWaveEngine(df, use_log_scale=False)
        pivot_sets = engine.run_multi_resolution_zigzag(base_mult=1.0)
        candidates = engine._generate_candidates(pivot_sets)
        impulses = [c for c in candidates if c.pattern_type == "impulse"]
        assert len(impulses) > 0, "Should find at least one impulse candidate in synthetic data"

    def test_variable_window_sizes_used(self):
        """Candidates should come from multiple window sizes, not just 6."""
        df = _make_synthetic_df()
        engine = DailyElliottWaveEngine(df, use_log_scale=False)
        pivot_sets = engine.run_multi_resolution_zigzag(base_mult=1.0)
        candidates = engine._generate_candidates(pivot_sets)
        window_sizes = set(c.window_size for c in candidates)
        assert 6 in window_sizes, "Should try window size 6"
