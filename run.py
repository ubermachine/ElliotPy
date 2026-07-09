import subprocess
import sys
import os

def check_and_install_dependencies():
    print("Checking dependencies...")
    try:
        import streamlit
        import yfinance
        import duckdb
        import pandas
        import pyarrow
        import numpy
        import scipy
        import plotly
        print("All dependencies are already installed.")
    except ImportError:
        print("Some dependencies are missing. Installing from requirements.txt...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
            print("Dependencies installed successfully.")
        except Exception as e:
            print(f"Error installing dependencies: {e}")
            sys.exit(1)

def run_streamlit():
    print("Starting Streamlit application...")
    # Add project root to Python path
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.dirname(os.path.abspath(__file__))
    try:
        subprocess.run([sys.executable, "-m", "streamlit", "run", "app.py"], env=env, check=True)
    except KeyboardInterrupt:
        print("\nStopping Streamlit server.")
    except Exception as e:
        print(f"Error starting Streamlit: {e}")

if __name__ == "__main__":
    check_and_install_dependencies()
    run_streamlit()
