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

# Another cache to store "cash" endpoint data
@st.cache_data(ttl=120)
def fetch_cash(key, secret):
    url = "https://live.trading212.com/api/v0/equity/account/cash"
    if secret:
        response = requests.get(url, auth=(API_KEY, sec_key))
    else:
        response = requests.get(url, headers={"Authorization": key})

    if response.status_code == 200:
        return response.json()
    else:
        st.error("Failed to fetch cash balance.")
        return None

# 4. Main App Logic
if API_KEY:
    positions = fetch_portfolio(API_KEY, sec_key)
    cash_info = fetch_cash(API_KEY, sec_key)

    if positions and cash_info:
        # ---------------------------------------------------------
        # NEW: The Merge Dictionary
        # Add any tickers here that you want to combine.
        # Format -> 'Exact_T212_Ticker': 'Your Custom Combined Name'
        # ---------------------------------------------------------
        TICKER_MERGES = {
            'GOOG_US_EQ': 'Alphabet (Combined)',
            'GOOGL_US_EQ': 'Alphabet (Combined)',
            # 'BRK.B_US_EQ': 'Berkshire (Combined)',
            # 'BRK.A_US_EQ': 'Berkshire (Combined)'
        }

        data = []

        # 1. Loop through your stocks
        for pos in positions:
            raw_ticker = pos.get('instrument', {}).get('ticker', 'Unknown')

            # Check if the ticker is in our merge list. If yes, rename it. If no, keep it.
            display_name = TICKER_MERGES.get(raw_ticker, raw_ticker)

            impact = pos.get('walletImpact', {})
            profit = impact.get('unrealizedProfitLoss', 0)
            cost = impact.get('totalCost', 0)
            current_val = impact.get('currentValue', 0)

            if current_val > 0:
                data.append({
                    'Ticker': display_name,  # Using the merged name!
                    'Current Value': current_val,
                    'Unrealized Profit': profit,
                    'Total Invested': cost
                })

        # 2. Inject Cash
        free_cash = cash_info.get('free', 0)
        data.append({
            'Ticker': '💵 CASH',
            'Current Value': free_cash,
            'Unrealized Profit': 0.0,
            'Total Invested': free_cash
        })

        # 3. Build the DataFrame and FUSE the duplicates
        df = pd.DataFrame(data)

        # This is the Pandas magic: Group by the Ticker name, and sum up all the numbers!
        df = df.groupby('Ticker', as_index=False).sum()

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

            # ... (This is the end of your previous code) ...
            # st.dataframe(display_df, use_container_width=True, hide_index=True)

            # ---------------------------------------------------------
            # NEW SECTION: Scrollable Chart Gallery
            # ---------------------------------------------------------
            st.divider()  # Draws a neat horizontal line across the page
            st.markdown("### 📊 Portfolio Visualizations")

            # Create a scrollable container box (500 pixels high)
            scroll_box = st.container(height=500, border=True)

            with scroll_box:
                # --- CHART 1: Bar Chart (Restored to Unrealized P/L) ---
                st.markdown("#### Unrealized Profit & Loss")

                # Create the Figure
                fig1, ax = plt.subplots(figsize=(10, 5))

                # Filter out CASH and sort by Unrealized Profit
                df_bar = df[df['Ticker'] != '💵 CASH'].sort_values(by='Unrealized Profit', ascending=True)

                # Restore the red/green dynamic coloring
                colors = ['#ff4c4c' if x < 0 else '#4caf50' for x in df_bar['Unrealized Profit']]

                # Plot the Unrealized Profit
                bars = ax.barh(df_bar['Ticker'], df_bar['Unrealized Profit'], color=colors, edgecolor='black')

                # Styling and Labels
                ax.set_xlabel("Unrealized Profit (£)", fontsize=10)
                ax.set_title("Live Portfolio Unrealized Profit & Loss", fontweight='bold')

                # Restore the exact value labels next to the bars
                for bar in bars:
                    xval = bar.get_width()
                    offset = (df_bar['Unrealized Profit'].max() * 0.05) if xval >= 0 else (
                                df_bar['Unrealized Profit'].max() * 0.1)
                    ha = 'left' if xval >= 0 else 'left'
                    ax.text(xval + offset, bar.get_y() + bar.get_height() / 2, f'{xval:+.2f}', va='center', ha=ha,
                            fontsize=10, fontweight='bold')

                # Add the zero line
                ax.axvline(0, color='black', linewidth=1.5, linestyle='--')

                # Pass the corrected chart to Streamlit
                st.pyplot(fig1)

                # --- Space between charts ---
                st.write("<br><br>", unsafe_allow_html=True)

                # --- CHART 2: Side-by-side Pie Charts ---
                st.markdown("#### Current Target vs. Actual Allocation")

                fig2, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))

                # Left Pie: User's Target Allocations
                # Filter out any 0% targets to keep the pie clean
                df_targets = df[df['Target %'] > 0]
                ax1.pie(df_targets['Target %'], labels=df_targets['Ticker'], autopct='%1.1f%%',
                        startangle=140, colors=plt.cm.Paired(range(len(df_targets))))
                ax1.set_title("Your Target Allocation", fontweight='bold')

                # Right Pie: Actual Current Allocations
                df_actual = df[df['Current Value'] > 0]
                ax2.pie(df_actual['Current Value'], labels=df_actual['Ticker'], autopct='%1.1f%%',
                        startangle=140, colors=plt.cm.Paired(range(len(df_actual))))
                ax2.set_title("Actual Current Allocation", fontweight='bold')

                # 3. Hand the second Figure to Streamlit
                st.pyplot(fig2)

else:
    st.info("👈 Enter your Trading 212 API Key in the sidebar to load your portfolio.")