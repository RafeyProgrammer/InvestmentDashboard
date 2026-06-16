import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime

st.set_page_config(page_title="Performance & News", layout="wide")
st.title("🎯 Portfolio Performance & Intelligence Hub")
st.caption("Cross-references your live holdings against institutional price targets and real-time news.")

# ─── 🔄 DATA STATE CHECK ───
# Ensure df_personal is populated from rebalancer.py
if "df_personal" in st.session_state and not st.session_state.df_personal.empty:
    df_source = st.session_state.df_personal.copy()

    # Prune out pure cash rows before hitting Yahoo Finance
    df_stocks = df_source[~df_source['Ticker'].str.contains("CASH|CASH", case=False, na=True)]

    if not df_stocks.empty:

        # ─── 🗂️ CREATING MULTI-TAB INTERFACE ───
        tab1, tab2 = st.tabs(["📊 Analyst Price Targets", "📰 Real-Time Portfolio News"])

        # =========================================================================
        # TAB 1: ANALYST PRICE TARGET MATRIX
        # =========================================================================
        with tab1:
            forecast_data = []
            unique_yf_tickers = {}  # Store mapped tickers to reuse for the news feed

            with st.spinner("Analyzing current price vs analyst target matrices..."):
                for _, row in df_stocks.iterrows():
                    clean_name = row['Ticker']
                    raw_ticker = row['Raw Ticker']

                    # ─── TRANSLATE TICKER FOR YAHOO FINANCE ───
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

                    # Save the mapped ticker for Tab 2
                    unique_yf_tickers[clean_name] = yf_ticker

                    try:
                        ticker_obj = yf.Ticker(yf_ticker)
                        info = ticker_obj.info

                        current_price = info.get("currentPrice", info.get("regularMarketPrice", 0.0))
                        low_target = info.get("targetLowPrice")
                        med_target = info.get("targetMedianPrice")
                        high_target = info.get("targetHighPrice")

                        # Distance formula calculation
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
                        forecast_data.append({
                            "Asset": clean_name, "Current Price": 0.0,
                            "Low Target": None, "Median Target": None, "High Target": None,
                            "To Low Target": None, "To Median Target": None, "To High Target": None
                        })

            df_forecast = pd.DataFrame(forecast_data)
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
            st.info(
                "💡 **Interpretation:** A positive green percentage indicates remaining upside potential to hit that target. Negative red means it has outgrown that forecast limit.")

            # =========================================================================
            # TAB 2: LIVE PORTFOLIO NEWS FEED (GUARANTEED FAIR DELIVERY)
            # =========================================================================
            with tab2:
                st.markdown("### 📰 Breaking Institutional Headlines")
                st.caption("Synchronized news wires separated by asset to ensure complete portfolio coverage.")

                with st.spinner("Fetching synchronized news wires..."):
                    # Loop through the mapped tickers one by one
                    for clean_name, yf_ticker in unique_yf_tickers.items():

                        # Create an expandable drop-down section for each stock
                        with st.expander(f"📁 Latest News for {clean_name}", expanded=True):
                            try:
                                stock_obj = yf.Ticker(yf_ticker)
                                ticker_news = stock_obj.news

                                ticker_articles = []

                                if ticker_news:
                                    for article in ticker_news:
                                        content = article.get("content", {})
                                        if not content:
                                            continue

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

                                        ticker_articles.append({
                                            "Headline": title,
                                            "Publisher": publisher,
                                            "Time": clean_time,
                                            "Link": link
                                        })

                                    # Sort this specific stock's news newest to oldest
                                    ticker_articles = sorted(ticker_articles, key=lambda x: x["Time"], reverse=True)

                                    # Render the articles strictly for this stock
                                    for item in ticker_articles[:5]:  # Show up to 5 articles per stock
                                        st.markdown(f"⏱️ **{item['Time']}** | *{item['Publisher']}*")
                                        st.markdown(f"🔗 [{item['Headline']}]({item['Link']})")
                                        st.markdown("---")
                                else:
                                    st.caption("📭 No recent media coverage indexed for this asset.")

                            except Exception as e:
                                st.caption("⚠️ Localized network latency timeout on this asset stream.")

            # Display the processed news array
            if ticker_articles:
                # Sort everything so the newest headlines from all stocks hit the top of the timeline
                sorted_news = sorted(ticker_articles, key=lambda x: x["Time"], reverse=True)

                # Render clean UI cards for each story
                for item in sorted_news[:32]:  # Display the top 15 breaking stories
                    with st.container(border=True):
                        col_news1, col_news2 = st.columns([1, 5])
                        with col_news1:
                            #st.markdown(f"### ` {item['Asset']} `")
                            st.caption(f"⏱️ {item['Time']}")
                        with col_news2:
                            st.markdown(f"**{item['Publisher']}**")
                            # HTML anchor rendering to make the headline link out smoothly
                            st.markdown(f"#### [{item['Headline']}]({item['Link']})")
            else:
                st.info("📭 No recent news wire data found for your current portfolio holdings.")

    else:
        st.warning("⚠️ No active stock allocations found in your portfolio to trace forecast markers against.")
else:
    st.info(
        "👈 Please make sure you have successfully entered your credentials and populated your assets inside the **Main Portfolio Tracker (rebalancer.py)** page first.")