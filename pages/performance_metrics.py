import streamlit as st
import pandas as pd
import yfinance as yf
import requests
from datetime import datetime

# ─── 🛠️ STREAMLIT PAGE ARCHITECTURE CONFIGURATIONS ───
st.set_page_config(page_title="Performance & Valuation", layout="wide")
st.title("🎯 Portfolio Performance & Valuation Hub")
st.caption("Cross-references live holdings against institutional metrics, news, and intrinsic value models.")

# ─── 👑 CLOUD-SAFE SECURE AGENT NETWORK SESSION INITIALIZATION ───
if "session" not in st.session_state:
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    })
    st.session_state.session = session

# ─── 🔄 SERVER STATE INTEGRITY AUDIT ───
if "df_personal" in st.session_state and not st.session_state.df_personal.empty:
    df_source = st.session_state.df_personal.copy()
    
    # Prune out flat cash rows before querying network pipelines
    df_stocks = df_source[~df_source['Ticker'].str.contains("CASH|CASH", case=False, na=True)]
    
    if not df_stocks.empty:
        
        # ─── 🗂️ THE THREE-TAB DASHBOARD GRID ───
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
                    
                    # ─── HOLISTIC TICKER TRANSLATION MATRIX ───
                    YAHOO_OVERRIDES = {
                        'IPOE_US_EQ': 'SOFI', 
                        'FB_US_EQ': 'META', 
                        'GOOG_US_EQ': 'GOOG', 
                        'GOOGL_US_EQ': 'GOOGL'
                    }
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
                        ticker_obj = yf.Ticker(yf_ticker, session=st.session_state.session)
                        info = ticker_obj.info
                        
                        current_price = info.get("currentPrice", info.get("regularMarketPrice", 0.0))
                        low_target = info.get("targetLowPrice")
                        med_target = info.get("targetMedianPrice")
                        high_target = info.get("targetHighPrice")
                        
                        dist_low = ((low_target - current_price) / current_price * 100) if low_target and current_price else None
                        dist_med = ((med_target - current_price) / current_price * 100) if med_target and current_price else None
                        dist_high = ((high_target - current_price) / current_price * 100) if high_target and current_price else None
                        
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
            
            # 🛡️ BULLETPROOF MOBILE RUNTIME FORMATTING FUNCTIONS
            safe_currency = lambda x: f"£{x:.2f}" if pd.notna(x) and isinstance(x, (int, float)) else "N/A"
            safe_percent = lambda x: f"{x:+.1f}%" if pd.notna(x) and isinstance(x, (int, float)) else "N/A"
            
            st.dataframe(
                df_forecast.style.format({
                    "Current Price": safe_currency, "Low Target": safe_currency, "Median Target": safe_currency, "High Target": safe_currency,
                    "To Low Target": safe_percent, "To Median Target": safe_percent, "To High Target": safe_percent
                }).map(
                    lambda x: "color: #ff4c4c;" if isinstance(x, (int, float)) and x < 0 else ("color: #4caf50;" if isinstance(x, (int, float)) and x > 0 else ""),
                    subset=["To Low Target", "To Median Target", "To High Target"]
                ), use_container_width=True, hide_index=True
            )
            st.info("💡 **Interpretation:** A positive green percentage indicates remaining growth runway to hit target. Negative red implies asset has currently outgrown that target limit.")

        # =========================================================================
        # TAB 2: LIVE PORTFOLIO NEWS FEED (GUARANTEED INDEPENDENT ALLOCATION)
        # =========================================================================
        with tab2:
            st.markdown("### 📰 Breaking Institutional Headlines")
            st.caption("Synchronized news wires separated by asset to ensure complete portfolio coverage.")
            
            with st.spinner("Fetching synchronized news wires..."):
                for clean_name, yf_ticker in unique_yf_tickers.items():
                    with st.expander(f"📁 Latest News for {clean_name}", expanded=True):
                        try:
                            stock_obj = yf.Ticker(yf_ticker, session=st.session_state.session)
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
                                        clean_time = datetime.strptime(raw_date_str, "%Y-%m-%dT%H:%M:%SZ").strftime('%Y-%m-%d %H:%M')
                                    except:
                                        clean_time = "Recent"
                                        
                                    click_url_dict = content.get("clickThroughUrl", {})
                                    link = click_url_dict.get("url", "#") if click_url_dict else "#"
                                    
                                    ticker_articles.append({"Headline": title, "Publisher": publisher, "Time": clean_time, "Link": link})
                                
                                # Chronological sorting per dropdown shelf
                                ticker_articles = sorted(ticker_articles, key=lambda x: x["Time"], reverse=True)
                                for item in ticker_articles[:4]:
                                    st.markdown(f"⏱️ **{item['Time']}** | *{item['Publisher']}*")
                                    st.markdown(f"🔗 [{item['Headline']}]({item['Link']})")
                                    st.markdown("---")
                            else:
                                st.caption("📭 No recent media coverage indexed for this asset.")
                        except Exception:
                            st.caption("⚠️ Localized network cloud latency timeout.")

        # =========================================================================
        # TAB 3: CUSTOM DCF VALUATION CALCULATOR (POLISHED COMPACT UNIT VISUALS)
        # =========================================================================
        with tab3:
            st.markdown("### 🧮 Intrinsic Valuation Engine (DCF)")
            st.caption("Select an asset to extract live financial line items and calculate its intrinsic fair value.")
            
            # 📖 CORE DCF OPERATIONAL EDUCATION EXPENDER PANEL
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
            
            selected_asset = st.selectbox("🎯 Target Asset to Value:", options=list(unique_yf_tickers.keys()))
            
            if selected_asset:
                target_yf = unique_yf_tickers[selected_asset]
                
                try:
                    with st.spinner(f"Extracting statement configurations for {target_yf}..."):
                        ticker_obj = yf.Ticker(target_yf, session=st.session_state.session)
                        info = ticker_obj.info
                        cashflow_df = ticker_obj.cashflow
                        
                        curr_price = info.get("currentPrice", info.get("regularMarketPrice", 1.0))
                        shares_outstanding = info.get("sharesOutstanding")
                        currency = info.get("currency", "$")
                        c_symbol = "£" if target_yf.endswith(".L") else currency
                        
                        baseline_fcf = None
                        if cashflow_df is not None and not cashflow_df.empty:
                            if "Free Cash Flow" in cashflow_df.index:
                                fcf_series = cashflow_df.loc["Free Cash Flow"]
                                baseline_fcf = fcf_series.iloc[0]
                        
                        if not baseline_fcf or pd.isna(baseline_fcf):
                            baseline_fcf = info.get("freeCashflow", 100000000)
                    
                    if shares_outstanding:
                        # 🧪 INTERNAL LEDGER INTERFACE STRUCTURAL FORMATTER
                        def format_compact(val):
                            if abs(val) >= 1_000_000_000:
                                return f"{c_symbol}{val / 1_000_000_000:.2f}B"
                            elif abs(val) >= 1_000_000:
                                return f"{c_symbol}{val / 1_000_000:.1f}M"
                            else:
                                return f"{c_symbol}{val:,.2f}"

                        st.markdown("#### ⚙️ Valuation Assumptions")
                        
                        # Automated default scale calculation
                        default_scale = "Billions" if abs(baseline_fcf) >= 1_000_000_000 else "Millions"
                        default_scaled_val = baseline_fcf / 1_000_000_000 if default_scale == "Billions" else baseline_fcf / 1_000_000

                        col_param1, col_param2 = st.columns([2, 1])
                        with col_param1:
                            input_val = st.number_input("Baseline Free Cash Flow (in chosen unit)", value=float(default_scaled_val), format="%.2f")
                        with col_param2:
                            unit_choice = st.selectbox("Unit Scale", options=["Billions", "Millions", "Absolute Value"], index=0 if default_scale == "Billions" else 1)
                        
                        # Convert localized layout values back up to true absolute integers
                        if unit_choice == "Billions": start_fcf = input_val * 1_000_000_000
                        elif unit_choice == "Millions": start_fcf = input_val * 1_000_000
                        else: start_fcf = input_val

                        col_p3, col_p4, col_p5 = st.columns(3)
                        with col_p3: growth_rate = st.slider("Expected Growth (Y1-5 %)", min_value=-20.0, max_value=50.0, value=10.0, step=1.0) / 100.0
                        with col_p4: discount_rate = st.slider("Required Return / Discount Rate (%)", min_value=5.0, max_value=20.0, value=9.0, step=0.5) / 100.0
                        with col_p5: terminal_growth = st.slider("Perpetual Terminal Growth (%)", min_value=0.0, max_value=5.0, value=2.5, step=0.1) / 100.0
                        
                        margin_of_safety = st.slider("Target Margin of Safety (%)", min_value=0.0, max_value=50.0, value=15.0, step=5.0) / 100.0
                        
                        # ─── THE MATH CORE PROCESSING MATRIX ───
                        projected_fcf = []
                        discounted_fcf = []
                        
                        current_fcf = start_fcf
                        for year in range(1, 6):
                            current_fcf = current_fcf * (1 + growth_rate)
                            df_factor = (1 + discount_rate) ** year
                            d_fcf = current_fcf / df_factor
                            
                            projected_fcf.append(current_fcf)
                            discounted_fcf.append(d_fcf)
                        
                        final_year_fcf = projected_fcf[-1]
                        terminal_value = (final_year_fcf * (1 + terminal_growth)) / (discount_rate - terminal_growth)
                        discounted_tv = terminal_value / ((1 + discount_rate) ** 5)
                        
                        intrinsic_value_equity = sum(discounted_fcf) + discounted_tv
                        fair_price_per_share = intrinsic_value_equity / shares_outstanding
                        margin_price = fair_price_per_share * (1 - margin_of_safety)
                        
                        # ─── VISUAL SCORE METRIC OUTPUT CARDS ───
                        st.markdown("---")
                        st.markdown("### 🎯 DCF Valuation Results")
                        
                        res_col1, res_col2, res_col3 = st.columns(3)
                        with res_col1:
                            st.metric(label="Current Market Price", value=f"{c_symbol}{curr_price:.2f}")
                        with res_col2:
                            delta_pct = ((fair_price_per_share - curr_price) / curr_price) * 100
                            st.metric(label="Estimated DCF Fair Value", value=f"{c_symbol}{fair_price_per_share:.2f}", delta=f"{delta_pct:+.1f}% Relative to Market")
                        with res_col3:
                            st.metric(label="Safe Buy Price (With Margin of Safety)", value=f"{c_symbol}{margin_price:.2f}")
                            
                        # Compact display matrix ledger summary
                        st.markdown("#### 📅 5-Year Cash Flow Projection Table")
                        projection_ledger = {
                            "Year": [f"Year {i}" for i in range(1, 6)],
                            "Projected FCF": [format_compact(x) for x in projected_fcf],
                            "Discounted Present Value": [format_compact(x) for x in discounted_fcf]
                        }
                        st.table(pd.DataFrame(projection_ledger))
                        st.caption(f"💡 **Terminal Value Note:** The present value of all cash flows beyond Year 5 evaluates to **{format_compact(discounted_tv)}** based on your terminal configurations.")
                    else:
                        st.error("❌ Unable to fetch total outstanding corporate shares required to split per-share metrics.")
                except Exception as e:
                    st.error(f"❌ Structural Statement Parsing Failure: {e}")
                    
    else:
        st.warning("⚠️ No active stock allocations found.")
else:
    st.info("👈 Please make sure you have successfully entered your credentials and populated your assets inside the **Main Portfolio Tracker (rebalancer.py)** page first.")
