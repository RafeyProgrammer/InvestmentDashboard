import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import requests
from streamlit.runtime.state import session_state

# 👑 CREATE A PERSISTENT AGENT SESSION AT THE TOP OF YOUR FILE
if "session" not in st.session_state:
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    })
    st.session_state.session = session

st.set_page_config(page_title="Performance & Valuation", layout="wide")
st.title("🎯 Portfolio Performance & Valuation Hub")
st.caption("Cross-references live holdings against institutional metrics, news, and intrinsic value models.")

# ─── DATA STATE CHECK ───
if "df_personal" in st.session_state and not st.session_state.df_personal.empty:
    df_source = st.session_state.df_personal.copy()
    df_stocks = df_source[~df_source['Ticker'].str.contains("CASH|CASH", case=False, na=True)]

    if not df_stocks.empty:
        # ─── THREE-TAB LAYOUT ───
        tab1, tab2, tab3 = st.tabs([
            "📊 Analyst Price Targets",
            "📰 Real-Time Portfolio News",
            "🧮 Custom DCF Valuation"
        ])

        unique_yf_tickers = {}

        # =========================================================================
        # TAB 1: ANALYST PRICE TARGET MATRIX
        # =========================================================================
        with tab1:
            forecast_data = []
            with st.spinner("Analyzing current price vs analyst target matrices..."):
                for _, row in df_stocks.iterrows():
                    clean_name = row['Ticker']
                    raw_ticker = row['Raw Ticker']

                    YAHOO_OVERRIDES = {'IPOE_US_EQ': 'SOFI', 'FB_US_EQ': 'META', 'GOOG_US_EQ': 'GOOG',
                                       'GOOGL_US_EQ': 'GOOGL'}
                    if raw_ticker in YAHOO_OVERRIDES:
                        yf_ticker = YAHOO_OVERRIDES[raw_ticker]
                    else:
                        base_ticker = raw_ticker.split('_')[0].strip()
                        base_upper = base_ticker.upper()
                        if "US" in raw_ticker:
                            yf_ticker = base_ticker
                        elif base_upper in ['RRL', 'RR']:
                            yf_ticker = 'RR.L'
                        elif "GB" in raw_ticker or "UK" in raw_ticker or "." not in base_ticker:
                            yf_ticker = f"{base_ticker}.L"
                        else:
                            yf_ticker = base_ticker

                    unique_yf_tickers[clean_name] = yf_ticker

                    try:
                        ticker_obj = yf.Ticker(yf_ticker,session=st.session_state.session)
                        info = ticker_obj.info
                        current_price = info.get("currentPrice", info.get("regularMarketPrice", 0.0))
                        low_target = info.get("targetLowPrice")
                        med_target = info.get("targetMedianPrice")
                        high_target = info.get("targetHighPrice")

                        dist_low = ((
                                                low_target - current_price) / current_price * 100) if low_target and current_price else None
                        dist_med = ((
                                                med_target - current_price) / current_price * 100) if med_target and current_price else None
                        dist_high = ((
                                                 high_target - current_price) / current_price * 100) if high_target and current_price else None

                        forecast_data.append({
                            "Asset": clean_name, "Current Price": current_price,
                            "Low Target": low_target, "Median Target": med_target, "High Target": high_target,
                            "To Low Target": dist_low, "To Median Target": dist_med, "To High Target": dist_high
                        })
                    except Exception:
                        forecast_data.append({
                            "Asset": clean_name, "Current Price": 0.0,
                            "Low Target": None, "Median Target": None, "High Target": None,
                            "To Low Target": None, "To Median Target": None, "To High Target": None
                        })

            df_forecast = pd.DataFrame(forecast_data)
            st.markdown("### 📋 Analyst Growth Runway Matrix")
            # ─── 🛡️ BULLETPROOF MOBILE FORMATTING FUNCTIONS ───
            # These safely ignore None/Null values so your mobile app never crashes
            safe_currency = lambda x: f"£{x:.2f}" if pd.notna(x) and isinstance(x, (int, float)) else "N/A"
            safe_percent = lambda x: f"{x:+.1f}%" if pd.notna(x) and isinstance(x, (int, float)) else "N/A"

            st.dataframe(
                df_forecast.style.format({
                    "Current Price": safe_currency,
                    "Low Target": safe_currency,
                    "Median Target": safe_currency,
                    "High Target": safe_currency,
                    "To Low Target": safe_percent,
                    "To Median Target": safe_percent,
                    "To High Target": safe_percent
                }).map(
                    lambda x: "color: #ff4c4c;" if isinstance(x, (int, float)) and x < 0 else (
                        "color: #4caf50;" if isinstance(x, (int, float)) and x > 0 else ""),
                    subset=["To Low Target", "To Median Target", "To High Target"]
                ),
                use_container_width=True,
                hide_index=True
            )

        # =========================================================================
        # TAB 2: LIVE PORTFOLIO NEWS FEED
        # =========================================================================
        with tab2:
            st.markdown("### 📰 Breaking Institutional Headlines")
            with st.spinner("Fetching synchronized news wires..."):
                for clean_name, yf_ticker in unique_yf_tickers.items():
                    with st.expander(f"📁 Latest News for {clean_name}", expanded=True):
                        try:
                            stock_obj = yf.Ticker(yf_ticker)
                            ticker_news = stock_obj.news
                            ticker_articles = []
                            if ticker_news:
                                for article in ticker_news:
                                    content = article.get("content", {})
                                    if not content: continue
                                    title = content.get("title", "No Title Available")
                                    provider = content.get("provider", {})
                                    publisher = provider.get("displayName", "Unknown Source")
                                    raw_date_str = content.get("pubDate", "")
                                    try:
                                        clean_time = datetime.strptime(raw_date_str, "%Y-%m-%dT%H:%M:%SZ").strftime(
                                            '%Y-%m-%d %H:%M')
                                    except:
                                        clean_time = "Recent"
                                    click_url_dict = content.get("clickThroughUrl", {})
                                    link = click_url_dict.get("url", "#") if click_url_dict else "#"

                                    ticker_articles.append(
                                        {"Headline": title, "Publisher": publisher, "Time": clean_time, "Link": link})

                                ticker_articles = sorted(ticker_articles, key=lambda x: x["Time"], reverse=True)
                                for item in ticker_articles[:4]:
                                    st.markdown(f"⏱️ **{item['Time']}** | *{item['Publisher']}*")
                                    st.markdown(f"🔗 [{item['Headline']}]({item['Link']})")
                                    st.markdown("---")
                            else:
                                st.caption("📭 No recent media coverage indexed for this asset.")
                        except Exception:
                            st.caption("⚠️ Localized network latency timeout.")

        # =========================================================================
        # TAB 3: CUSTOM DCF VALUATION CALCULATOR
        # =========================================================================
        with tab3:
            st.markdown("### 🧮 Intrinsic Intrinsic Valuation Engine (DCF)")
            st.caption("Select an asset to extract live financial line items and calculate its intrinsic fair value.")

            # ─── 🎓 NEW: INTERACTIVE DCF OPERATIONAL EXPLAINER ───
            with st.expander("📖 Quick Start Guide: How to Use the DCF Model Safely", expanded=False):
                st.markdown("""
                            A Discounted Cash Flow (DCF) model estimates what a company is worth today based on how much cash it will generate in the future. 
                            Here is how to adjust the inputs like a professional analyst:

                            1. **Baseline FCF (Free Cash Flow):** * *What it is:* The actual cash a company has left over after paying all operating expenses and capital expenditures (CapEx).
                               * *How to use:* The app automatically pulls the most recent official annual figure. If the company had a weird one-off year (e.g., a massive lawsuit payout or unusual asset sale), you can normalize this number up or down.

                            2. **Expected FCF Growth (Years 1-5 %):** * *What it is:* The annualized speed at which you think the company will grow its cash flow over the next 5 years.
                               * *How to use:* Be conservative! While hyper-growth tech stocks might grow at 30%+ for a year or two, matching that across a full 5-year macro cycle is rare. Slower, stable companies usually chart between **5% to 12%**. High-growth rockets usually trend between **15% to 25%**.

                            3. **Required Return / Discount Rate (%):** * *What it is:* Your hurdle rate. The minimum annual return you require to justify the risk of buying this specific stock instead of a safe index fund.
                               * *How to use:* Standard institutional practice uses **9% to 10%** for stable mega-caps (like Apple or Microsoft) and **11% to 14%** for more volatile, high-beta, or smaller companies to account for the extra risk.

                            4. **Perpetual Terminal Growth Rate (%):** * *What it is:* The rate at which the company will grow forever after Year 5. Mathematically, a company cannot grow faster than the economy it operates in forever.
                               * *How to use:* Keep this strictly between **2.0% and 3.0%** (typically **2.5%**). This aligns with long-term baseline GDP growth and global inflation targets.

                            5. **Target Margin of Safety (%):** * *What it is:* Your built-in insurance policy against being wrong about your growth assumptions.
                               * *How to use:* If the model says a stock is worth £100, a **15% Margin of Safety** tells you to wait to buy until the market price drops to £85. Set this higher (20-30%) for unpredictable tech stocks and lower (10-15%) for highly predictable utilities or blue chips.
                            """)


            # Select target portfolio stock
            selected_asset = st.selectbox("🎯 Target Asset to Value:", options=list(unique_yf_tickers.keys()))

            if selected_asset:
                target_yf = unique_yf_tickers[selected_asset]

                try:
                    with st.spinner(f"Extracting statement configurations for {target_yf}..."):
                        ticker_obj = yf.Ticker(target_yf)
                        info = ticker_obj.info
                        cashflow_df = ticker_obj.cashflow

                        # 1. Fetch current price and structural shares outstanding
                        curr_price = info.get("currentPrice", info.get("regularMarketPrice", 1.0))
                        shares_outstanding = info.get("sharesOutstanding")
                        currency = info.get("currency", "$")
                        c_symbol = "£" if target_yf.endswith(".L") else currency

                        # 2. Extract baseline Free Cash Flow from statement data frame
                        baseline_fcf = None
                        if cashflow_df is not None and not cashflow_df.empty:
                            if "Free Cash Flow" in cashflow_df.index:
                                fcf_series = cashflow_df.loc["Free Cash Flow"]
                                baseline_fcf = fcf_series.iloc[0]  # Take the most recent annual reporting item

                        # Fallback calculation if yfinance misses the explicit index item
                        if not baseline_fcf or pd.isna(baseline_fcf):
                            baseline_fcf = info.get("freeCashflow", 100000000)  # Default to 100M if missing completely

                    if shares_outstanding:
                        # ─── INTERACTIVE INPUT MODEL BLOCK ───
                        col_param1, col_param2, col_param3 = st.columns(3)
                        with col_param1:
                            start_fcf = st.number_input(f"Baseline FCF ({c_symbol})", value=float(baseline_fcf),
                                                        step=1000000.0, format="%.0f")
                        with col_param2:
                            growth_rate = st.slider("Expected FCF Growth (Years 1-5 %)", min_value=-20.0,
                                                    max_value=50.0, value=10.0, step=1.0) / 100.0
                        with col_param3:
                            discount_rate = st.slider("Required Return / Discount Rate (%)", min_value=5.0,
                                                      max_value=20.0, value=9.0, step=0.5) / 100.0

                        col_param4, col_param5 = st.columns(2)
                        with col_param4:
                            terminal_growth = st.slider("Perpetual Terminal Growth Rate (%)", min_value=0.0,
                                                        max_value=5.0, value=2.5, step=0.1) / 100.0
                        with col_param5:
                            margin_of_safety = st.slider("Target Margin of Safety (%)", min_value=0.0, max_value=50.0,
                                                         value=15.0, step=5.0) / 100.0

                        # ─── 📊 THE MATHEMATICAL DCF ENGINE ───
                        projected_fcf = []
                        discounted_fcf = []

                        # Calculate Year 1 to 5 Projections
                        current_fcf = start_fcf
                        for year in range(1, 6):
                            current_fcf = current_fcf * (1 + growth_rate)
                            # Formula: $PV = \frac{FV}{(1 + r)^t}$
                            df_factor = (1 + discount_rate) ** year
                            d_fcf = current_fcf / df_factor

                            projected_fcf.append(current_fcf)
                            discounted_fcf.append(d_fcf)

                        # Calculate Terminal Value (Gordon Growth Model Method)
                        # Formula: $TV = \frac{FCF_5 \times (1 + g_{terminal})}{r - g_{terminal}}$
                        final_year_fcf = projected_fcf[-1]
                        terminal_value = (final_year_fcf * (1 + terminal_growth)) / (discount_rate - terminal_growth)
                        discounted_tv = terminal_value / ((1 + discount_rate) ** 5)

                        # Total Present Value Matrix Summation
                        intrinsic_value_equity = sum(discounted_fcf) + discounted_tv
                        fair_price_per_share = intrinsic_value_equity / shares_outstanding
                        margin_price = fair_price_per_share * (1 - margin_of_safety)

                        # ─── VISUAL OUTPUT MATRIX CARDS ───
                        st.markdown("---")
                        st.markdown("### 🎯 DCF Valuation Results")

                        res_col1, res_col2, res_col3 = st.columns(3)
                        with res_col1:
                            st.metric(label="Current Market Price", value=f"{c_symbol}{curr_price:.2f}")
                        with res_col2:
                            delta_pct = ((fair_price_per_share - curr_price) / curr_price) * 100
                            st.metric(
                                label="Estimated DCF Fair Value",
                                value=f"{c_symbol}{fair_price_per_share:.2f}",
                                delta=f"{delta_pct:+.1f}% Relative to Market"
                            )
                        with res_col3:
                            st.metric(label="Safe Buy Price (With Margin of Safety)",
                                      value=f"{c_symbol}{margin_price:.2f}")

                        # Render calculation ledger step table
                        st.markdown("#### 📅 5-Year Cash Flow Projection Table")
                        projection_ledger = {
                            "Year": [f"Year {i}" for i in range(1, 6)],
                            "Projected FCF": [f"{c_symbol}{x:,.0f}" for x in projected_fcf],
                            "Discounted Present Value": [f"{c_symbol}{x:,.0f}" for x in discounted_fcf]
                        }
                        st.table(pd.DataFrame(projection_ledger))
                        st.caption(
                            f"💡 **Terminal Value Note:** The present value of all cash flows beyond Year 5 is calculated as **{c_symbol}{discounted_tv:,.0f}** based on your terminal growth assumptions.")
                    else:
                        st.error(
                            "❌ Unable to fetch total outstanding corporate shares required to split per-share metrics.")
                except Exception as e:
                    st.error(f"❌ Structural Statement Parsing Failure: {e}")

    else:
        st.warning("⚠️ No active stock allocations found.")
else:
    st.info("👈 Please make sure you have active assets tracking in rebalancer.py first.")