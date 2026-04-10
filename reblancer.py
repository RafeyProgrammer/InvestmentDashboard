import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt

# 1. Page Configuration
st.set_page_config(page_title="T212 Rebalancer", layout="wide")
st.title("⚖️ Live Portfolio Rebalancing Calculator")

# 2. Sidebar for Secure API Entry (No hardcoding!)
st.sidebar.header("Connection")
API_KEY = st.sidebar.text_input("API Key", type="password")
sec_key = st.sidebar.text_input("API Secret", type="password", help="...")


# 3. Caching the API Call (Stores data for 60 seconds to prevent rate limits)
@st.cache_data(ttl=60)
def fetch_portfolio(key, secret):
    url = "https://live.trading212.com/api/v0/equity/positions"
    if secret:
        response = requests.get(url, auth=(API_KEY, sec_key))
    else:
        response = requests.get(url, headers={"Authorization": API_KEY})

    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Connection Failed: {response.status_code} - {response.text}")
        return None


# 4. Main App Logic
if API_KEY:
    positions = fetch_portfolio(API_KEY, sec_key)

    if positions:
        # Extract Data
        data = []
        for pos in positions:
            ticker = pos.get('instrument', {}).get('ticker', 'Unknown')
            current_val = pos.get('walletImpact', {}).get('currentValue', 0)
            if current_val > 0:  # Only include active positions
                data.append({'Ticker': ticker, 'Current Value': current_val})

        df = pd.DataFrame(data)
        total_value = df['Current Value'].sum()

        st.subheader(f"Total Portfolio Value: £{total_value:,.2f}")

        # --- INTERACTIVE UI: SLIDERS ---
        st.markdown("### 🎯 Set Target Allocations")
        col1, col2 = st.columns([1, 2])  # Split screen for layout

        with col1:
            st.write("Adjust your desired percentages below:")
            targets = {}
            total_target_pct = 0

            # Generate a slider for every ticker automatically
            for ticker in df['Ticker']:
                # Default slider to current percentage to start
                current_pct = (df.loc[df['Ticker'] == ticker, 'Current Value'].values[0] / total_value) * 100
                targets[ticker] = st.slider(f"{ticker} Target %", min_value=0, max_value=100, value=int(current_pct),
                                            step=1)
                total_target_pct += targets[ticker]

            # Warning if they don't add up to 100%
            if total_target_pct != 100:
                st.warning(f"Total Target: {total_target_pct}% (Should equal 100%)")
            else:
                st.success("Allocations equal exactly 100%!")

        # --- MATH & RESULTS ---
        with col2:
            # Map the user's slider inputs back to the DataFrame
            df['Target %'] = df['Ticker'].map(targets) / 100
            df['Target Value (£)'] = total_value * df['Target %']
            df['Action Amount (£)'] = df['Target Value (£)'] - df['Current Value']


            # Formatting the Action column
            def format_action(val):
                if val > 1:
                    return f"🟢 BUY £{abs(val):.2f}"
                elif val < -1:
                    return f"🔴 SELL £{abs(val):.2f}"
                return "⚪ HOLD"


            df['Action'] = df['Action Amount (£)'].apply(format_action)

            # Display the interactive table
            st.markdown("### 📋 Action Plan")
            display_df = df[['Ticker', 'Current Value', 'Target Value (£)', 'Action']]
            st.dataframe(display_df, use_container_width=True, hide_index=True)

else:
    st.info("👈 Enter your Trading 212 API Key in the sidebar to load your portfolio.")