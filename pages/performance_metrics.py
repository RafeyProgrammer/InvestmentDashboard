import streamlit as st
import pandas as pd
import yfinance as yf

st.set_page_config(page_title="Performance Metrics",layout="wide")
st.title("Wall Street price targets")
st.caption("See what the 'street' thinks of your stocks! compare your own forecasts to that of the experts"
           "have you got a wall street favourite or a black sheep? ")

# ─── 🔄 DATA STATE CHECK ───
# Pull the shared workspace directly from your rebalancer.py memory state
if "df_personal" in st.session_state and not st.session_state.df_personal.empty:
    df_source = st.session_state.df_personal.copy()

    # Prune out pure cash representations before hitting Yahoo Finance
    df_stocks = df_source[~df_source['Ticker'].str.contains("CASH|CASH", case=False, na=True)]

    if not df_stocks.empty:
        forecast_data = []

        # Display a sleek global scanner banner while background processing runs
        with st.spinner("Analyzing current price vs analyst target matrices..."):
            for _, row in df_stocks.iterrows():
                clean_name = row['Ticker']
                raw_ticker = row['Raw Ticker']

                # ─── 🛠️ UPGRADED BULLETPROOF TICKER TRANSLATOR ───
                YAHOO_OVERRIDES = {
                    'IPOE_US_EQ': 'SOFI',
                    'FB_US_EQ': 'META',
                    'GOOG_US_EQ': 'GOOG',
                    'GOOGL_US_EQ': 'GOOGL'
                }

                if raw_ticker in YAHOO_OVERRIDES:
                    yf_ticker = YAHOO_OVERRIDES[raw_ticker]
                else:
                    # Strip away common Trading 212 transaction suffixes
                    base_ticker = raw_ticker.split('_')[0].strip()

                    # Force a clean uppercase comparison to match LSE tickers accurately
                    base_upper = base_ticker.upper()

                    # Explicit UK/LSE handling
                    if "US" in raw_ticker:
                        # It's explicitly a US stock
                        yf_ticker = base_ticker
                    elif base_upper in ['RRL', 'RR']:
                        # Handle Rolls-Royce specific anomalies
                        yf_ticker = 'RR.L'
                    elif "GB" in raw_ticker or "UK" in raw_ticker or "." not in base_ticker:
                        # Fallback: If it's not a US stock, or if it lacks a dot, append the LSE marker (.L)
                        # This catches standard UK tickers like LGEN, VOD, BARC, etc.
                        yf_ticker = f"{base_ticker}.L"
                    else:
                        yf_ticker = base_ticker

                try:
                    # Fetch live analyst targets out of Yahoo's info dictionary
                    ticker_obj = yf.Ticker(yf_ticker)
                    info = ticker_obj.info

                    current_price = info.get("currentPrice", info.get("regularMarketPrice", 0.0))
                    low_target = info.get("targetLowPrice")
                    med_target = info.get("targetMedianPrice")
                    high_target = info.get("targetHighPrice")

                    # ─── MATH MATRIX COMPILATION ENGINE ───
                    # Distance formula: ((Target - Current) / Current) * 100
                    dist_low = ((
                                            low_target - current_price) / current_price * 100) if low_target and current_price else None
                    dist_med = ((
                                            med_target - current_price) / current_price * 100) if med_target and current_price else None
                    dist_high = ((
                                             high_target - current_price) / current_price * 100) if high_target and current_price else None

                    forecast_data.append({
                        "Asset": clean_name,
                        "Current Price": current_price,
                        "Low Target": low_target,
                        "Median Target": med_target,
                        "High Target": high_target,
                        "To Low Target": dist_low,
                        "To Median Target": dist_med,
                        "To High Target": dist_high
                    })

                except Exception:
                    # Graceful fallback handler if yfinance rate-limits a specific asset line
                    forecast_data.append({
                        "Asset": clean_name, "Current Price": 0.0,
                        "Low Target": None, "Median Target": None, "High Target": None,
                        "To Low Target": None, "To Median Target": None, "To High Target": None
                    })

        # ─── 📊 THE PRESENTATION LAYER ───
        df_forecast = pd.DataFrame(forecast_data)

        # Style layout mapping instructions for Streamlit's st.dataframe engine
        st.markdown("### 📋 Analyst Growth Runway Matrix")

        st.dataframe(
            df_forecast.style.format({
                "Current Price": "£{:.2f}",
                "Low Target": "£{:.2f}",
                "Median Target": "£{:.2f}",
                "High Target": "£{:.2f}",
                "To Low Target": "{:+.1f}%",
                "To Median Target": "{:+.1f}%",
                "To High Target": "{:+.1f}%"
            }).map(
                lambda x: "color: #ff4c4c;" if isinstance(x, (int, float)) and x < 0 else (
                    "color: #4caf50;" if isinstance(x, (int, float)) and x > 0 else ""),
                subset=["To Low Target", "To Median Target", "To High Target"]
            ),
            use_container_width=True,
            hide_index=True
        )

        # Informational operational notice
        st.info(
            "💡 **How to interpret table values:** A positive green percentage indicates how much the asset needs to rally to reach that analyst target. A negative red percentage means the stock is currently trading above that specific forecast projection.")

    else:
        st.warning("⚠️ No active stock allocations found in your portfolio to trace forecast markers against.")
else:
    st.info(
        "👈 Please make sure you have successfully entered your credentials and populated your assets inside the **Main Portfolio Tracker (rebalancer.py)** page first.")