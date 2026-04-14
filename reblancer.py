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

# ---------------------------------------------------------
# HELPER FUNCTIONS (Defined outside tabs to prevent crashes)
        # ---------------------------------------------------------
def format_action(val):
    if val > 1: return f"🟢 BUY £{abs(val):.2f}"
    elif val < -1: return f"🔴 SELL £{abs(val):.2f}"
    return "HOLD"

# 3. Caching the API Call (Stores data for 60 seconds to prevent rate limits)
@st.cache_data(ttl=300)
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
@st.cache_data(ttl=300)
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
# ... (Keep your imports and @st.cache_data functions at the top exactly as they are) ...

if API_KEY:
    positions = fetch_portfolio(API_KEY, sec_key)
    cash_info = fetch_cash(API_KEY, sec_key)

    if positions and cash_info:
        TICKER_MERGES = {
            'GOOG_US_EQ': 'Alphabet (Combined)',
            'GOOGL_US_EQ': 'Alphabet (Combined)'
        }

        # We now need TWO separate lists
        personal_data = []
        pie_data = []

        # 1. Loop and mathematically split the data
        for pos in positions:
            raw_ticker = pos.get('instrument', {}).get('ticker', 'Unknown')
            display_name = TICKER_MERGES.get(raw_ticker, raw_ticker)

            # Get the share counts to calculate the split ratio
            qty_total = pos.get('quantity', 0)
            qty_personal = pos.get('quantityAvailableForTrading', 0)
            qty_pie = pos.get('quantityInPies', 0)

            impact = pos.get('walletImpact', {})
            profit = impact.get('unrealizedProfitLoss', 0)
            cost = impact.get('totalCost', 0)
            current_val = impact.get('currentValue', 0)

            if current_val > 0 and qty_total > 0:
                # Calculate what percentage belongs to you vs the Pie
                personal_ratio = qty_personal / qty_total
                pie_ratio = qty_pie / qty_total

                # Append to Personal Portfolio (if you own any outside the pie)
                if qty_personal > 0:
                    personal_data.append({
                        'Ticker': display_name,
                        'Current Value': current_val * personal_ratio,
                        'Unrealized Profit': profit * personal_ratio,
                        'Total Invested': cost * personal_ratio
                    })

                # Append to Managed Pie Portfolio (if any are inside a pie)
                if qty_pie > 0:
                    pie_data.append({
                        'Ticker': display_name,
                        'Current Value': current_val * pie_ratio,
                        'Unrealized Profit': profit * pie_ratio,
                        'Total Invested': cost * pie_ratio
                    })

        # 2. Inject Cash (Assuming all uninvested free cash belongs to your main portfolio)
        free_cash = cash_info.get('free', 0)
        personal_data.append({
            'Ticker': '💵 CASH', 'Current Value': free_cash,
            'Unrealized Profit': 0.0, 'Total Invested': free_cash
        })

        # 3. Build & Combine the DataFrames
        df_personal = pd.DataFrame(personal_data)
        if not df_personal.empty:
            df_personal = df_personal.groupby('Ticker', as_index=False).sum()

        df_pie = pd.DataFrame(pie_data)
        if not df_pie.empty:
            df_pie = df_pie.groupby('Ticker', as_index=False).sum()

            # ---------------------------------------------------------
            # NEW UI: STREAMLIT TABS WITH EMBEDDED CHARTS
            # ---------------------------------------------------------
            tab1, tab2 = st.tabs(["📈 Main Portfolio (Personal)", "🥧 Managed Portfolio (Pie)"])

            # === TAB 1: MAIN PORTFOLIO ===
            with tab1:
                if not df_personal.empty:
                    total_personal = df_personal['Current Value'].sum()
                    st.subheader(f"Personal Value: £{total_personal:,.2f}")

                    # --- Personal Rebalancing Calculator ---
                    st.markdown("### 🎯 Rebalance Personal Portfolio")
                    col1_pers, col2_pers = st.columns([1, 2])

                    with col1_pers:
                        st.write("Adjust target allocations:")
                        pers_targets = {}
                        pers_total_target_pct = 0

                        for ticker in df_personal['Ticker']:
                            current_pct = (df_personal.loc[df_personal['Ticker'] == ticker, 'Current Value'].values[
                                               0] / total_personal) * 100
                            pers_targets[ticker] = st.slider(f"{ticker} Target %", 0, 100, int(current_pct), 1,
                                                             key=f"main_{ticker}")
                            pers_total_target_pct += pers_targets[ticker]

                        if pers_total_target_pct != 100:
                            st.warning(f"Total Target: {pers_total_target_pct}% (Should equal 100%)")
                        else:
                            st.success("100% Allocated!")

                    with col2_pers:
                        df_personal['Target %'] = df_personal['Ticker'].map(pers_targets) / 100
                        df_personal['Target Value (£)'] = total_personal * df_personal['Target %']
                        df_personal['Action Amount (£)'] = df_personal['Target Value (£)'] - df_personal[
                            'Current Value']

                        # Using the safely defined helper function
                        df_personal['Action'] = df_personal['Action Amount (£)'].apply(format_action)

                        st.markdown("### 📋 Personal Action Plan")
                        st.dataframe(df_personal[['Ticker', 'Current Value', 'Target Value (£)', 'Action']],
                                     use_container_width=True, hide_index=True)

                    # --- TAB 1 CHARTS: Allocation Pie AND P/L Bar Chart ---
                    st.divider()
                    st.markdown("### 📊 Personal Portfolio Visualizations")

                    fig1, (ax_pie1, ax_bar1) = plt.subplots(1, 2, figsize=(14, 6))

                    # 1. Left Chart: The Pie Allocation (Dynamic)
                    df_pers_sorted = df_personal.sort_values(by='Current Value', ascending=False)

                    if pers_total_target_pct == 100:
                        pers_chart_data = df_pers_sorted['Target %']
                        pers_pie_title = "Target Personal Allocation"
                    else:
                        pers_chart_data = df_pers_sorted['Current Value']
                        pers_pie_title = "Current Personal Allocation"

                    ax_pie1.pie(pers_chart_data, labels=df_pers_sorted['Ticker'], autopct='%1.1f%%',
                                colors=plt.cm.Paired(range(len(df_pers_sorted))),
                                wedgeprops={'edgecolor': 'white', 'linewidth': 1})
                    ax_pie1.set_title(pers_pie_title, fontweight='bold')

                    # 2. Right Chart: The P/L Bar Chart
                    df_pers_bar = df_personal[df_personal['Ticker'] != '💵 CASH'].sort_values(by='Unrealized Profit',
                                                                                             ascending=True)

                    # SAFETY CHECK: Only draw the bar chart if they actually own stocks (not just cash)
                    if not df_pers_bar.empty:
                        colors1 = ['#ff4c4c' if x < 0 else '#4caf50' for x in df_pers_bar['Unrealized Profit']]
                        bars1 = ax_bar1.barh(df_pers_bar['Ticker'], df_pers_bar['Unrealized Profit'], color=colors1,
                                             edgecolor='black')

                        ax_bar1.set_xlabel("Unrealized Profit (£)", fontsize=10)
                        ax_bar1.set_title("Personal Unrealized P/L", fontweight='bold')

                        max_profit_pers = max(abs(df_pers_bar['Unrealized Profit'].max()),
                                              abs(df_pers_bar['Unrealized Profit'].min()), 1)
                        for bar in bars1:
                            xval = bar.get_width()
                            offset = (max_profit_pers * 0.05) if xval >= 0 else (max_profit_pers * 0.1)
                            ha = 'left' if xval >= 0 else 'left'
                            ax_bar1.text(xval + offset, bar.get_y() + bar.get_height() / 2, f'{xval:+.2f}', va='center',
                                         ha=ha, fontsize=10, fontweight='bold')

                        ax_bar1.axvline(0, color='black', linewidth=1.5, linestyle='--')
                    else:
                        ax_bar1.text(0.5, 0.5, "No Active Stocks (Only Cash)", ha='center', va='center', fontsize=12)
                        ax_bar1.axis('off')

                    plt.tight_layout()
                    st.pyplot(fig1)
                    plt.close(fig1)  # CRITICAL FIX: Clears memory instantly to prevent hanging
                else:
                    st.info("No active personal investments found.")

            # === TAB 2: MANAGED PIE ===
            with tab2:
                if not df_pie.empty:
                    total_pie = df_pie['Current Value'].sum()
                    st.subheader(f"Managed Pie Value: £{total_pie:,.2f}")

                    st.markdown("### 🎯 Rebalance Managed Pie")
                    col1_pie, col2_pie = st.columns([1, 2])

                    with col1_pie:
                        st.write("Adjust target allocations for the Pie:")
                        pie_targets = {}
                        pie_total_target_pct = 0

                        for ticker in df_pie['Ticker']:
                            current_pct = (df_pie.loc[df_pie['Ticker'] == ticker, 'Current Value'].values[
                                               0] / total_pie) * 100
                            pie_targets[ticker] = st.slider(f"{ticker} Target %", 0, 100, int(current_pct), 1,
                                                            key=f"pie_{ticker}")
                            pie_total_target_pct += pie_targets[ticker]

                        if pie_total_target_pct != 100:
                            st.warning(f"Total Target: {pie_total_target_pct}% (Should equal 100%)")
                        else:
                            st.success("100% Allocated!")

                    with col2_pie:
                        df_pie['Target %'] = df_pie['Ticker'].map(pie_targets) / 100
                        df_pie['Target Value (£)'] = total_pie * df_pie['Target %']
                        df_pie['Action Amount (£)'] = df_pie['Target Value (£)'] - df_pie['Current Value']

                        df_pie['Action'] = df_pie['Action Amount (£)'].apply(format_action)

                        st.markdown("### 📋 Pie Action Plan")
                        st.dataframe(df_pie[['Ticker', 'Current Value', 'Target Value (£)', 'Action']],
                                     use_container_width=True, hide_index=True)

                    st.divider()
                    st.markdown("### 📊 Managed Pie Visualizations")

                    fig2, (ax_pie, ax_bar) = plt.subplots(1, 2, figsize=(14, 6))

                    df_pie_sorted = df_pie.sort_values(by='Current Value', ascending=False)

                    if pie_total_target_pct == 100:
                        pie_chart_data = df_pie_sorted['Target %']
                        pie_title = "Target Pie Allocation"
                    else:
                        pie_chart_data = df_pie_sorted['Current Value']
                        pie_title = "Current Pie Allocation"

                    ax_pie.pie(pie_chart_data, labels=df_pie_sorted['Ticker'], autopct='%1.1f%%',
                               colors=plt.cm.Paired(range(len(df_pie_sorted))),
                               wedgeprops={'edgecolor': 'white', 'linewidth': 1})
                    ax_pie.set_title(pie_title, fontweight='bold')

                    df_pie_bar = df_pie.sort_values(by='Unrealized Profit', ascending=True)

                    if not df_pie_bar.empty:
                        colors2 = ['#ff4c4c' if x < 0 else '#4caf50' for x in df_pie_bar['Unrealized Profit']]
                        bars2 = ax_bar.barh(df_pie_bar['Ticker'], df_pie_bar['Unrealized Profit'], color=colors2,
                                            edgecolor='black')

                        ax_bar.set_xlabel("Unrealized Profit (£)", fontsize=10)
                        ax_bar.set_title("Pie Unrealized P/L", fontweight='bold')

                        max_profit_pie = max(abs(df_pie_bar['Unrealized Profit'].max()),
                                             abs(df_pie_bar['Unrealized Profit'].min()), 1)
                        for bar in bars2:
                            xval = bar.get_width()
                            offset = (max_profit_pie * 0.05) if xval >= 0 else (max_profit_pie * 0.1)
                            ha = 'left' if xval >= 0 else 'left'
                            ax_bar.text(xval + offset, bar.get_y() + bar.get_height() / 2, f'{xval:+.2f}', va='center',
                                        ha=ha, fontsize=10, fontweight='bold')

                        ax_bar.axvline(0, color='black', linewidth=1.5, linestyle='--')

                    plt.tight_layout()
                    st.pyplot(fig2)
                    plt.close(fig2)  # CRITICAL FIX: Clears memory instantly

                else:
                    st.info("No active Pies found in this account.")

else:
    st.info("👈 Enter your Trading 212 API Key in the sidebar to load your portfolio.")