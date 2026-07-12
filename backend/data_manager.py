import os
import datetime
import pandas as pd
import numpy as np
import duckdb
import yfinance as yf

class DataManager:
    def __init__(self, db_path="data_cache.db", parquet_dir="data"):
        # Parameters kept for backward compatibility but ignored
        pass

    def _get_data_path(self, symbol: str, interval: str = "1d") -> str:
        """Determines if a local data lake exists, otherwise returns GitHub URL."""
        symbol_sanitized = symbol.replace("^", "").replace(".", "_").lower()
        filename = f"{symbol_sanitized}_{interval}.parquet"
        
        # Check local paths first
        local_paths = [
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "market-data-lake", "data", filename)),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "market-data-lake", "data", filename)),
            os.path.join("D:\\antigravity_sandbox\\market-data-lake\\data", filename)
        ]
        for path in local_paths:
            if os.path.exists(path):
                return path.replace("\\", "/")
                
        # Default to raw GitHub URL
        github_user = os.getenv("GITHUB_USER", "HP")
        github_repo = os.getenv("GITHUB_REPO", "market-data-lake")
        return f"https://raw.githubusercontent.com/{github_user}/{github_repo}/main/data/{filename}"

    def fetch_data(self, symbol: str, force_refresh: bool = False) -> tuple[pd.DataFrame, bool]:
        """
        Fetches daily OHLCV data directly from the central Parquet file.
        Uses DuckDB to query the Parquet path (local or remote URL).
        """
        symbol = symbol.upper().strip()
        data_path = self._get_data_path(symbol)
        
        print(f"Streaming data for {symbol} from {data_path}...")
        
        con = duckdb.connect()
        try:
            # Load httpfs if reading from HTTPS URL
            if data_path.startswith("http"):
                con.execute("INSTALL httpfs; LOAD httpfs;")
                
            query = f"SELECT Date, Open, High, Low, Close, Volume FROM '{data_path}' ORDER BY Date"
            df = con.execute(query).df()
        except Exception as e:
            print(f"Failed to load from lake: {e}. Falling back to dynamic yfinance download...")
            try:
                import yfinance as yf
                yf_df = yf.download(symbol, period="10y", progress=False)
                if yf_df.empty:
                    raise ValueError(f"yfinance returned empty data for {symbol}")
                if isinstance(yf_df.columns, pd.MultiIndex):
                    yf_df.columns = yf_df.columns.get_level_values(0)
                df = yf_df.reset_index()
                
                # Normalize column names
                rename_map = {}
                for col in df.columns:
                    col_lower = str(col).lower()
                    if col_lower == 'date' or col_lower == 'datetime':
                        rename_map[col] = 'Date'
                    elif col_lower in ['open', 'high', 'low', 'close', 'volume']:
                        rename_map[col] = col_lower.capitalize()
                df = df.rename(columns=rename_map)
                df = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
            except Exception as yf_err:
                raise ValueError(f"Failed to load data for '{symbol}' from data lake AND yfinance: {yf_err}")
        finally:
            con.close()

            
        # Ensure Date is datetime.date
        df['Date'] = pd.to_datetime(df['Date']).dt.date
        
        # Scale selection (Log scale if 5-year range exceeds 200%)
        last_5_years = df.tail(1260)
        min_close = last_5_years['Close'].min()
        max_close = last_5_years['Close'].max()
        range_pct = (max_close - min_close) / min_close if min_close > 0 else 0
        use_log_scale = range_pct > 2.0
        
        print(f"Processed dataset: {len(df)} bars. Log scale required: {use_log_scale} (Range: {range_pct:.1%}).")
        return df, use_log_scale

    def sync_incremental(self, symbol: str) -> tuple[pd.DataFrame, bool]:
        """Backward compatibility helper. Simply fetches the latest from the lake."""
        return self.fetch_data(symbol)

