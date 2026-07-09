# ElliotPy 🌊

ElliotPy is an advanced, high-performance Elliott Wave engine and interactive visualization dashboard built with Python and Streamlit. It automates top-down fractal wave analysis on financial markets, applying complex structural rules to identify motives (impulses/diagonals) and corrections (zigzags/flats).

![ElliotPy Dashboard](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![DuckDB](https://img.shields.io/badge/DuckDB-FFF000?style=for-the-badge&logo=duckdb&logoColor=black)
![Plotly](https://img.shields.io/badge/Plotly-3F4F75?style=for-the-badge&logo=plotly&logoColor=white)

## 🚀 Features

- **Automated Wave Labeling:** Recursively maps 5-wave motive structures and 3-wave corrections across the entire chart.
- **Top-Down Fractal Engine:** Analyzes macro degrees (Cycle, Primary) down to micro degrees (Minor, Minuette) using dynamic Zig-Zag thresholds.
- **Strict Structural Rule Engine:** Enforces Elliott Wave laws (e.g., W3 cannot be shortest, W4 cannot overlap W1 territory) and scores setups based on Fibonacci extensions.
- **Lightning-Fast WebGL Rendering:** Plots thousands of daily candles instantly using hardware-accelerated `go.Scattergl`.
- **Trading Dashboard:** Generates actionable trade recommendations based on the active wave count (Target, Invalidation Price, and Risk/Reward).
- **GitHub Sync Integration:** Seamlessly fetch incremental daily data from Yahoo Finance and push updated databases directly back to GitHub from the Streamlit UI.

## 🛠️ Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/ubermachine/ElliotPy.git
   cd ElliotPy
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the dashboard:**
   ```bash
   python run.py
   ```
   *The Streamlit app will automatically launch in your browser at `http://localhost:8501`.*

## ☁️ Streamlit Cloud Deployment

ElliotPy is fully equipped to be hosted on Streamlit Cloud. 
If you want to use the in-app **"Resync & Push to GitHub"** feature on the cloud, you must configure two Streamlit Secrets in your app settings:

```toml
GITHUB_TOKEN = "ghp_your_personal_access_token_here"
GITHUB_REPO = "ubermachine/ElliotPy"
```
*(Ensure your Personal Access Token has write permissions to the repository).*

## 📈 Supported Assets
ElliotPy currently caches daily data for:
- `^SPX` (S&P 500)
- `AAPL` (Apple Inc.)
- `BTC-USD` (Bitcoin)
- `GC=F` (Gold Futures)
- `SI=F` (Silver Futures)

## 📄 License
MIT License. Feel free to fork, modify, and integrate ElliotPy into your own trading strategies!
