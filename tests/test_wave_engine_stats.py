import pandas as pd
import numpy as np
from backend.wave_engine import DailyElliottWaveEngine, WaveNode, Pivot

def create_sample_df():
    dates = pd.date_range("2024-01-01", periods=100)
    prices = 100.0 + np.cumsum(np.random.normal(0.5, 1.0, 100))
    df = pd.DataFrame({
        "Date": dates,
        "Open": prices,
        "High": prices + 1.0,
        "Low": prices - 1.0,
        "Close": prices,
        "Volume": 1000,
        "RSI": 55.0,
        "MACD": 0.5,
        "MACD_Signal": 0.2,
        "MACD_Hist": 0.3
    })
    return df

def test_calculate_enhanced_stats():
    df = create_sample_df()
    engine = DailyElliottWaveEngine(df, use_log_scale=False)
    p1 = Pivot(0, 100.0, np.log(100.0), "LOW", df['Date'].iloc[0])
    p2 = Pivot(10, 120.0, np.log(120.0), "HIGH", df['Date'].iloc[10])
    wave = WaveNode(p1, p2, "1", "Primary", "motive")
    wave.score = 8.0
    
    stats = engine.calculate_enhanced_stats([wave], [])
    assert "phase" in stats
    assert "progress_pct" in stats
    assert "fib_harmony_score" in stats
    assert "atr_context" in stats
    assert "momentum_status" in stats

def test_generate_tactical_tips():
    df = create_sample_df()
    engine = DailyElliottWaveEngine(df, use_log_scale=False)
    p1 = Pivot(0, 100.0, np.log(100.0), "LOW", df['Date'].iloc[0])
    p2 = Pivot(10, 120.0, np.log(120.0), "HIGH", df['Date'].iloc[10])
    wave = WaveNode(p1, p2, "1", "Primary", "motive")
    wave.score = 8.0
    trade_rec = {"bias": "Bullish", "target": 130.0, "invalidation": 95.0, "current_price": 120.0}
    
    tips = engine.generate_tactical_tips([wave], trade_rec)
    assert "entry_tip" in tips
    assert "stop_tip" in tips
    assert "exit_tip" in tips
