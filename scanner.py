import pandas as pd
import yfinance as yf
import numpy as np
import matplotlib.pyplot as plt
import requests
from oauthlib.oauth2.rfc6749.clients import AUTH_HEADER

"""Objective of this code:
- Scan assets and provide Basic indicator readings
- Provide Momentum readings
- Provide Valuation and financial data
- Provide price targets
- Provide visualisation of portfolio"""

# First get Trading212 API working

link = "https://live.trading212.com/api/v0"

import base64


# 1. Your credentials
API_KEY = "1372668ZhQuWrzdCPWLYGukvlDWwXsyvhzzh"
sec_key = "_rjWgHtKSQARaNU_eApiNeMcpD0sO-z53VkrpTJCJZs"

# 2. Combine them into a single string

credentials_string = f"{API_KEY}:{sec_key}"


# 3. Encode the string to bytes, then Base64 encode it

encoded_credentials = base64.b64encode(credentials_string.encode('utf-8')).decode('utf-8')


# 4. The final header value

auth_header = f"Basic {encoded_credentials}"


print(auth_header)


# 2. Set the URL (Demo or Live)
#url = "https://live.trading212.com/api/v0/equity/account/summary"
url = "https://live.trading212.com/api/v0/equity/positions"

# 3. Make the request using the auth= parameter
# DO NOT include the Authorization header, the auth parameter handles it.
response = requests.get(url, auth=(API_KEY, sec_key))
print(response.json())
# 4. Print results
if response.status_code == 200:
    positions = response.json()

    # 3. Extract all data into a single, unified list
    portfolio_data = []

    for pos in positions:
        ticker = pos.get('instrument', {}).get('name', 'Unknown')
        impact = pos.get('walletImpact', {})

        # Extract our three core metrics
        profit = impact.get('unrealizedProfitLoss', 0)
        cost = impact.get('totalCost', 0)
        current_val = impact.get('currentValue', 0)  # NEW: Includes P/L

        portfolio_data.append({
            'Ticker': ticker,
            'Unrealized Profit': profit,
            'Total Invested': cost,
            'Current Value': current_val
        })

    df = pd.DataFrame(portfolio_data)

    # --- ADD THIS AFTER YOUR DATAFRAME IS CREATED (df = pd.DataFrame(portfolio_data)) ---

    # 1. Define your target percentages here (Decimals must add up to 1.0)
    # Make sure the keys match the EXACT tickers returned by the API
    target_allocations = {
        'Rolls-Royce': 0.35,  # 35% Target
        'Alphabet (Class C)': 0.10,
        'Alphabet (Class A)': 0.10,
        'Palantir': 0.3,
        'Tesla': 0.10,
        "SoFi Technologies": 0.05
    }

    # 2. Map the target percentages to your DataFrame
    df['Target %'] = df['Ticker'].map(target_allocations)

    # Check if any tickers are missing from your target list
    if df['Target %'].isnull().any():
        print("WARNING: Some assets in your portfolio do not have a defined Target %.")
        # Fill missing with 0% so the math doesn't break
        df['Target %'] = df['Target %'].fillna(0)

        # 3. Calculate the Rebalancing Math
    total_portfolio_value = df['Current Value'].sum()

    # What the cash value SHOULD be
    df['Target Value (£)'] = total_portfolio_value * df['Target %']

    # The difference (Target - Current)
    df['Rebalance Amount (£)'] = df['Target Value (£)'] - df['Current Value']


    # 4. Create a readable action column
    def determine_action(amount):
        if amount > 5:  # £5 buffer to prevent tiny fractional trades
            return f"BUY £{amount:.2f}"
        elif amount < -5:
            return f"SELL £{abs(amount):.2f}"
        else:
            return "HOLD (On Target)"


    df['Action Required'] = df['Rebalance Amount (£)'].apply(determine_action)

    # 5. Print a clean summary table to your terminal
    print("\n" + "=" * 50)
    print("PORTFOLIO REBALANCING SUMMARY")
    print("=" * 50)
    print(f"Total Portfolio Value: £{total_portfolio_value:,.2f}")
    print("-" * 50)
    # Select only the columns we want to see in the terminal
    summary_df = df[['Ticker', 'Current Value', 'Target %', 'Rebalance Amount (£)', 'Action Required']]
    print(summary_df.to_string(index=False))
    print("=" * 50 + "\n")

    # Write df to csv file for further analysis
    summary_df.to_csv("Rebalance.csv",sep="|",index=False)

    if df.empty or (df['Total Invested'].sum() == 0 and df.iloc[0]['Ticker'] == 'Unknown'):
        print("Data extraction failed. Check payload structure.")
    else:
        # -----------------------------------------------------------------
        # CHART 1: The Bar Chart (Unrealized Profit/Loss)
        # -----------------------------------------------------------------
        df_bar = df.sort_values(by='Unrealized Profit', ascending=True)

        plt.figure(figsize=(10, 6))
        colors = ['#ff4c4c' if x < 0 else '#4caf50' for x in df_bar['Unrealized Profit']]
        bars = plt.barh(df_bar['Ticker'], df_bar['Unrealized Profit'], color=colors, edgecolor='black')

        plt.xlabel("Unrealized Profit (Account Currency)", fontsize=12)
        plt.ylabel("Asset Ticker", fontsize=12)
        plt.title("Live Portfolio Unrealized Profit & Loss", fontsize=14, fontweight='bold')

        for bar in bars:
            xval = bar.get_width()
            offset = (df_bar['Unrealized Profit'].max() * 0.02) if xval >= 0 else -(
                        df_bar['Unrealized Profit'].max() * 0.02)
            ha = 'left' if xval >= 0 else 'right'
            plt.text(xval + offset, bar.get_y() + bar.get_height() / 2, f'{xval:+.2f}', va='center', ha=ha, fontsize=10,
                     fontweight='bold')

        plt.axvline(0, color='black', linewidth=1.5, linestyle='--')
        plt.margins(x=0.15)
        plt.tight_layout()
        print("Bar chart displayed. Close the window to view the Allocation Pie Charts.")
        plt.savefig("PL.jpg")
        plt.show()

        # -----------------------------------------------------------------
        # CHART 2 & 3: Side-by-Side Pie Charts (Invested vs. Current Value)
        # -----------------------------------------------------------------
        sum_invested = df['Total Invested'].sum()
        sum_current = df['Current Value'].sum()

        if sum_invested > 0 and sum_current > 0:
            # Create a layout with 1 row and 2 columns
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7))
            fig.suptitle("Portfolio Allocation: Initial vs. Current", fontsize=16, fontweight='bold')

            # --- Left Pie: Total Invested ---
            # Sort data so slices look organized
            df_invested = df.sort_values(by='Total Invested', ascending=False)
            ax1.pie(df_invested['Total Invested'],
                    labels=df_invested['Ticker'],
                    autopct='%1.1f%%',
                    startangle=140,
                    colors=plt.cm.Paired(range(len(df_invested))),
                    wedgeprops={'edgecolor': 'white', 'linewidth': 1})
            ax1.set_title(f"Initial Allocation (Total Invested)\nTotal: £{sum_invested:,.2f}", fontsize=12)

            # --- Right Pie: Current Value (Includes P/L) ---
            df_current = df.sort_values(by='Current Value', ascending=False)
            ax2.pie(df_current['Current Value'],
                    labels=df_current['Ticker'],
                    autopct='%1.1f%%',
                    startangle=140,
                    colors=plt.cm.Paired(range(len(df_current))),
                    wedgeprops={'edgecolor': 'white', 'linewidth': 1})
            ax2.set_title(f"True Allocation (Current Value w/ P&L)\nTotal: £{sum_current:,.2f}", fontsize=12)

            plt.tight_layout()
            plt.savefig("Allocation.jpg")
            plt.show()

        else:
            print("Total values are zero. Pie charts cannot be generated.")

else:
    print(f"Error {response.status_code}: {response.text}")

