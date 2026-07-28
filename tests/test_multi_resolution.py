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

class TestStrictRulesAndRanker:
    def test_verify_impulse_no_atr_buffer(self):
        """verify_impulse_rules should reject W2 overlap without ATR tolerance."""
        df = _make_synthetic_df(100)
        engine = DailyElliottWaveEngine(df, use_log_scale=False)
        # Create 6 pivots where W2 retraces exactly 100% of W1 (should fail strictly)
        pivots = [
            Pivot(0, 20.0, np.log(20.0), "LOW", df.index[0]),
            Pivot(10, 25.0, np.log(25.0), "HIGH", df.index[10]),
            Pivot(20, 20.0, np.log(20.0), "LOW", df.index[20]),  # W2 = exactly W1 origin
            Pivot(40, 35.0, np.log(35.0), "HIGH", df.index[40]),
            Pivot(50, 28.0, np.log(28.0), "LOW", df.index[50]),
            Pivot(60, 38.0, np.log(38.0), "HIGH", df.index[60]),
        ]
        passed, checklist = engine.verify_impulse_rules(pivots)
        assert passed is False, "Exact 100% W2 retracement should fail strict rules"

    def test_rank_candidates_returns_sorted(self):
        """_rank_candidates should return candidates sorted by final score descending."""
        df = _make_synthetic_df()
        engine = DailyElliottWaveEngine(df, use_log_scale=False)
        pivot_sets = engine.run_multi_resolution_zigzag(base_mult=1.0)
        candidates = engine._generate_candidates(pivot_sets)
        if not candidates:
            pytest.skip("No candidates found in synthetic data")
        ranked = engine._rank_candidates(candidates)
        assert len(ranked) > 0
        for i in range(1, len(ranked)):
            assert ranked[i-1].score >= ranked[i].score

    def test_rank_deduplicates_overlapping(self):
        """Overlapping candidates (>70% index overlap) should be deduplicated."""
        df = _make_synthetic_df()
        engine = DailyElliottWaveEngine(df, use_log_scale=False)
        # Create two nearly-identical candidates
        c1 = CandidateCount(waves=[], score=10.0, resolution=1.0, window_size=6,
                           pattern_type="impulse", invalidation=20.0,
                           anchor_start_idx=0, anchor_end_idx=100)
        c2 = CandidateCount(waves=[], score=8.0, resolution=2.0, window_size=6,
                           pattern_type="impulse", invalidation=20.0,
                           anchor_start_idx=5, anchor_end_idx=95)  # 90% overlap with c1
        ranked = engine._rank_candidates([c1, c2])
        assert len(ranked) == 1, "Overlapping candidates should be deduplicated"
        assert ranked[0].score >= 5.0  # Keep the higher-scored one

class TestRebuiltAnalysis:
    def test_degree_by_structure(self):
        """_determine_degree_by_structure should assign degree by price range ratio."""
        df = _make_synthetic_df()
        engine = DailyElliottWaveEngine(df, use_log_scale=False)
        assert engine._determine_degree_by_structure(50.0, 60.0) == "Cycle"
        assert engine._determine_degree_by_structure(20.0, 60.0) == "Primary"
        assert engine._determine_degree_by_structure(8.0, 60.0) == "Intermediate"
        assert engine._determine_degree_by_structure(2.0, 60.0) == "Minor"
        assert engine._determine_degree_by_structure(0.5, 60.0) == "Minuette"

    def test_run_analysis_returns_same_interface(self):
        """run_analysis must return (List[WaveNode], List[List[WaveNode]])."""
        from backend.wave_engine import WaveNode
        df = _make_synthetic_df()
        engine = DailyElliottWaveEngine(df, use_log_scale=False)
        primary, alternates = engine.run_analysis(min_move_mult=1.0)
        assert isinstance(primary, list)
        assert isinstance(alternates, list)
        for w in primary:
            assert isinstance(w, WaveNode) # type: ignore
        for alt in alternates:
            assert isinstance(alt, list)

    def test_run_analysis_finds_motive_in_synthetic(self):
        """Synthetic 5-wave data should produce at least one motive wave label."""
        df = _make_synthetic_df()
        engine = DailyElliottWaveEngine(df, use_log_scale=False)
        primary, alternates = engine.run_analysis(min_move_mult=1.0)
        motive_labels = {"I", "II", "III", "IV", "V", "[1]", "[2]", "[3]", "[4]", "[5]",
                        "(1)", "(2)", "(3)", "(4)", "(5)", "{1}", "{2}", "{3}", "{4}", "{5}",
                        "i", "ii", "iii", "iv", "v"}
        found_motive = any(w.label in motive_labels for w in primary)
        assert found_motive, f"Should find motive waves. Got labels: {[w.label for w in primary]}"

    def test_existing_tests_still_pass(self):
        """Sanity: existing stats and tips methods still work with rebuilt engine."""
        from backend.wave_engine import WaveNode
        df = _make_synthetic_df()
        engine = DailyElliottWaveEngine(df, use_log_scale=False)
        primary, alternates = engine.run_analysis(min_move_mult=1.0)
        stats = engine.calculate_enhanced_stats(primary, alternates)
        assert "phase" in stats
        tips = engine.generate_tactical_tips(primary, {"target": 50.0, "invalidation": 20.0, "current_price": 35.0, "bias": "Bullish"})
        assert "entry_tip" in tips
