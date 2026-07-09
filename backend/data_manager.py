import os
import datetime
import pandas as pd
import numpy as np
import duckdb
import yfinance as yf

class DataManager:
    def __init__(self, db_path="data_cache.db", parquet_dir="data"):
        self.db_path = db_path
        self.parquet_dir = parquet_dir
        os.makedirs(self.parquet_dir, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initializes the DuckDB cache database schema."""
        conn = duckdb.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS price_history (
                    symbol VARCHAR,
                    date DATE,
                    open DOUBLE,
                    high DOUBLE,
                    low DOUBLE,
                    close DOUBLE,
                    volume BIGINT,
                    PRIMARY KEY (symbol, date)
                )
            """)
        finally:
            conn.close()

    def fetch_data(self, symbol: str, force_refresh: bool = False) -> tuple[pd.DataFrame, bool]:
        """
        Fetches daily OHLCV data for a given symbol.
        Checks DuckDB cache, updates if outdated, writes to Parquet fallback,
        cleans gaps, validates length, and returns clean DataFrame + log_scale flag.
        """
        symbol = symbol.upper().strip()
        data_loaded = False
        df = None

        if not force_refresh:
            # Try to load from DuckDB
            df = self._read_from_duckdb(symbol)
            if df is not None and len(df) >= 1250:
                # Check if up to date (latest date is close to today)
                latest_date = pd.to_datetime(df['Date'].max()).date()
                today = datetime.date.today()
                # If latest date is less than 3 days old (handles weekends), consider up-to-date
                if (today - latest_date).days <= 3:
                    data_loaded = True
                    print(f"Loaded {len(df)} bars for {symbol} from DuckDB cache.")
            
            # Try to load from Parquet if DuckDB load failed
            if not data_loaded:
                df = self._read_from_parquet(symbol)
                if df is not None and len(df) >= 1250:
                    latest_date = pd.to_datetime(df['Date'].max()).date()
                    today = datetime.date.today()
                    if (today - latest_date).days <= 3:
                        data_loaded = True
                        print(f"Loaded {len(df)} bars for {symbol} from Parquet fallback cache.")
                        # Restore to DuckDB cache
                        self._write_to_duckdb(symbol, df)

        if not data_loaded:
            # Download from yfinance
            print(f"Fetching fresh data for {symbol} from yfinance...")
            try:
                # Fetch 10 years to ensure we exceed 1,250 daily bars comfortably
                ticker = yf.Ticker(symbol)
                yf_df = ticker.history(period="10y")
                if yf_df.empty:
                    # Fallback to standard download
                    yf_df = yf.download(symbol, period="10y")
                
                if yf_df.empty:
                    raise ValueError(f"No data returned for symbol '{symbol}' from Yahoo Finance.")
                
                # Format DataFrame
                df = yf_df.reset_index()
                # Normalize column names
                rename_map = {}
                for col in df.columns:
                    if col.lower() == 'date':
                        rename_map[col] = 'Date'
                    elif col.lower() == 'open':
                        rename_map[col] = 'Open'
                    elif col.lower() == 'high':
                        rename_map[col] = 'High'
                    elif col.lower() == 'low':
                        rename_map[col] = 'Low'
                    elif col.lower() == 'close':
                        rename_map[col] = 'Close'
                    elif col.lower() == 'volume':
                        rename_map[col] = 'Volume'
                
                df = df.rename(columns=rename_map)
                # Keep only core columns
                df = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
                # Ensure Date is simple date
                df['Date'] = pd.to_datetime(df['Date']).dt.date
                
                # Write to caches
                self._write_to_duckdb(symbol, df)
                self._write_to_parquet(symbol, df)
                print(f"Fetched and cached {len(df)} bars for {symbol}.")
            except Exception as e:
                # If yfinance failed, try reading whatever we have in cache even if slightly outdated
                print(f"Yahoo Finance fetch failed: {e}. Attempting cached data fallback...")
                df = self._read_from_duckdb(symbol)
                if df is None:
                    df = self._read_from_parquet(symbol)
                if df is None:
                    raise ValueError(f"Failed to fetch data for '{symbol}' and no cached copy is available.")

        # Pre-process data
        df = self._preprocess_data(df)

        # Scale selection (Log scale if 5-year range exceeds 200%)
        # Let's inspect the last 5 years of the data for this check
        last_5_years = df.tail(1260)
        min_close = last_5_years['Close'].min()
        max_close = last_5_years['Close'].max()
        range_pct = (max_close - min_close) / min_close if min_close > 0 else 0
        use_log_scale = range_pct > 2.0
        
        print(f"Processed dataset: {len(df)} bars. Log scale required: {use_log_scale} (Range: {range_pct:.1%}).")
        return df, use_log_scale

    def sync_incremental(self, symbol: str) -> tuple[pd.DataFrame, bool]:
        """
        Incrementally downloads only the missing prices since the last date in the cache,
        updates DuckDB & Parquet, and returns the full cleaned historical dataset.
        """
        symbol = symbol.upper().strip()
        # Read what we currently have in DuckDB
        df_cached = self._read_from_duckdb(symbol)
        if df_cached is None:
            df_cached = self._read_from_parquet(symbol)
            
        # If cache is totally empty, we must download the full history
        if df_cached is None or len(df_cached) == 0:
            print(f"Cache empty for {symbol}. Fetching full history...")
            return self.fetch_data(symbol, force_refresh=True)

        latest_date = pd.to_datetime(df_cached['Date'].max()).date()
        today = datetime.date.today()
        
        # Check if we already have today's data or it's a weekend and we are up to date
        if (today - latest_date).days <= 0:
            print(f"Data for {symbol} is already up to date. Latest date: {latest_date}.")
            df_cleaned = self._preprocess_data(df_cached)
            # Recalculate scale
            last_5_years = df_cleaned.tail(1260)
            min_close = last_5_years['Close'].min()
            max_close = last_5_years['Close'].max()
            use_log = ((max_close - min_close) / min_close if min_close > 0 else 0) > 2.0
            return df_cleaned, use_log

        # Fetch only the missing range
        start_date = latest_date + datetime.timedelta(days=1)
        print(f"Syncing {symbol} incrementally from {start_date} to {today}...")
        try:
            ticker = yf.Ticker(symbol)
            # Get data since start_date
            yf_df = ticker.history(start=start_date.strftime("%Y-%m-%d"))
            if yf_df.empty:
                # Try download fallback
                yf_df = yf.download(symbol, start=start_date.strftime("%Y-%m-%d"))
            
            if not yf_df.empty:
                # Format
                df_new = yf_df.reset_index()
                rename_map = {}
                for col in df_new.columns:
                    if col.lower() == 'date': rename_map[col] = 'Date'
                    elif col.lower() == 'open': rename_map[col] = 'Open'
                    elif col.lower() == 'high': rename_map[col] = 'High'
                    elif col.lower() == 'low': rename_map[col] = 'Low'
                    elif col.lower() == 'close': rename_map[col] = 'Close'
                    elif col.lower() == 'volume': rename_map[col] = 'Volume'
                df_new = df_new.rename(columns=rename_map)
                df_new = df_new[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
                df_new['Date'] = pd.to_datetime(df_new['Date']).dt.date
                
                # Combine cached and new data
                df_combined = pd.concat([df_cached, df_new], ignore_index=True)
                # Drop duplicate dates, keeping the latest downloaded version
                df_combined = df_combined.drop_duplicates(subset=['Date'], keep='last')
                
                # Save the updated combined dataset
                self._write_to_duckdb(symbol, df_combined)
                self._write_to_parquet(symbol, df_combined)
                print(f"Incremental sync successful. Added {len(df_new)} new bars.")
                df_cached = df_combined
            else:
                print("No new data found on Yahoo Finance.")
        except Exception as e:
            print(f"Incremental sync failed: {e}. Falling back to cached data.")
            
        df_cleaned = self._preprocess_data(df_cached)
        
        # Scale selection
        last_5_years = df_cleaned.tail(1260)
        min_close = last_5_years['Close'].min()
        max_close = last_5_years['Close'].max()
        range_pct = (max_close - min_close) / min_close if min_close > 0 else 0
        use_log_scale = range_pct > 2.0
        
        return df_cleaned, use_log_scale

    def _preprocess_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Cleans gaps: forward-fills at most 2 consecutive days.
        Deletes any bar with remaining NaNs.
        Validates minimum length of 1,250 bars.
        """
        df = df.copy()
        # Sort by date
        df = df.sort_values('Date').reset_index(drop=True)
        
        # Forward fill at most 2 consecutive days
        cols_to_fill = ['Open', 'High', 'Low', 'Close', 'Volume']
        df[cols_to_fill] = df[cols_to_fill].ffill(limit=2)
        
        # Delete entire bar if still contains NaNs (gaps > 2 days)
        df = df.dropna(subset=['Close'])
        df = df.reset_index(drop=True)
        
        # Validate minimum bar length
        if len(df) < 1250:
            raise ValueError(f"Insufficient historical data. Found {len(df)} valid daily bars, minimum required is 1,250.")
            
        return df

    def _read_from_duckdb(self, symbol: str) -> pd.DataFrame | None:
        """Reads cached price data from DuckDB."""
        conn = duckdb.connect(self.db_path)
        try:
            res = conn.execute(
                "SELECT date, open, high, low, close, volume FROM price_history WHERE symbol = ? ORDER BY date",
                [symbol]
            ).fetchall()
            if not res:
                return None
            df = pd.DataFrame(res, columns=['Date', 'Open', 'High', 'Low', 'Close', 'Volume'])
            # Ensure Date is python datetime.date
            df['Date'] = pd.to_datetime(df['Date']).dt.date
            return df
        except Exception as e:
            print(f"DuckDB read error: {e}")
            return None
        finally:
            conn.close()

    def _write_to_duckdb(self, symbol: str, df: pd.DataFrame):
        """Writes price data to DuckDB using UPSERT logic."""
        conn = duckdb.connect(self.db_path)
        try:
            # We can register the dataframe and do an upsert
            conn.register('df_temp', df)
            conn.execute(f"""
                INSERT OR REPLACE INTO price_history (symbol, date, open, high, low, close, volume)
                SELECT '{symbol}', Date, Open, High, Low, Close, Volume FROM df_temp
            """)
        except Exception as e:
            print(f"DuckDB write error: {e}")
        finally:
            conn.close()

    def _read_from_parquet(self, symbol: str) -> pd.DataFrame | None:
        """Reads cached price data from Parquet file."""
        file_path = os.path.join(self.parquet_dir, f"{symbol.lower()}_daily.parquet")
        if not os.path.exists(file_path):
            return None
        try:
            df = pd.read_parquet(file_path)
            # Ensure Date is simple date
            df['Date'] = pd.to_datetime(df['Date']).dt.date
            return df
        except Exception as e:
            print(f"Parquet read error: {e}")
            return None

    def _write_to_parquet(self, symbol: str, df: pd.DataFrame):
        """Writes price data to Parquet file."""
        file_path = os.path.join(self.parquet_dir, f"{symbol.lower()}_daily.parquet")
        try:
            df_write = df.copy()
            # Convert date to timestamp for Parquet compatibility
            df_write['Date'] = pd.to_datetime(df_write['Date'])
            df_write.to_parquet(file_path, index=False)
        except Exception as e:
            print(f"Parquet write error: {e}")
