"""
AI Stock Insight Assistant
Enter a stock name and get AI-powered insights in simple language.
"""

import streamlit as st
import yfinance as yf
import os
from dotenv import load_dotenv
import altair as alt
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

# Configure page
st.set_page_config(
    page_title="StockLens - AI Stock Insights",
    page_icon="📈",
    layout="centered"
)

# Initialize saved symbols and defaults in session state
if 'saved_symbols' not in st.session_state:
    st.session_state['saved_symbols'] = []

# Sidebar: indicator settings and saved symbols
with st.sidebar:
    st.header("Chart & Indicator Settings")
    st.number_input("EMA short period", min_value=5, max_value=200, value=20, step=1, key='ema_short')
    st.number_input("EMA long period", min_value=10, max_value=400, value=50, step=1, key='ema_long')
    st.number_input("RSI period", min_value=5, max_value=50, value=14, step=1, key='rsi_period')
    st.markdown("---")
    st.header("Personalization")
    st.selectbox("Risk profile", options=["Conservative", "Balanced", "Aggressive"], index=1, key='risk_profile')
    st.selectbox("Investment horizon", options=["Short", "Medium", "Long"], index=1, key='horizon')
    st.selectbox("Insight style", options=["Concise", "Detailed"], index=0, key='insight_style')
    st.markdown("---")
    st.header("Saved Symbols")
    if st.session_state['saved_symbols']:
        for s in st.session_state['saved_symbols']:
            if st.button(s, key=f"load_{s}"):
                st.session_state['stock_input'] = s
    else:
        st.write("No saved symbols yet.")

# Initialize OpenAI client
def get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        # Try to get from config.py if .env not set
        try:
            import config
            api_key = config.OPENAI_API_KEY
        except:
            pass
    if api_key:
        try:
            import openai
            return openai.OpenAI(api_key=api_key)
        except ImportError:
            return None
    return None


def fetch_stock_data(symbol):
    """Fetch stock data using yfinance."""
    try:
        ticker = yf.Ticker(symbol)
        
        # Get info
        info = ticker.info
        current_price = info.get('currentPrice', info.get('regularMarketPreviousClose', 'N/A'))
        previous_close = info.get('regularMarketPreviousClose', 'N/A')
        market_cap = info.get('marketCap', 'N/A')
        pe_ratio = info.get('trailingPE', 'N/A')
        volume = info.get('volume', 'N/A')
        high_52w = info.get('fiftyTwoWeekHigh', 'N/A')
        low_52w = info.get('fiftyTwoWeekLow', 'N/A')
        
        # Get historical data for trend analysis
        hist = ticker.history(period="6mo")
        
        return {
            "symbol": symbol,
            "name": info.get('shortName', info.get('longName', symbol)),
            "current_price": current_price,
            "previous_close": previous_close,
            "market_cap": market_cap,
            "pe_ratio": pe_ratio,
            "volume": volume,
            "high_52w": high_52w,
            "low_52w": low_52w,
            "history": hist
        }
    except Exception as e:
        return {"error": str(e)}


def analyze_trends(history):
    """Analyze stock trends from historical data."""
    if history is None or len(history) == 0:
        return {
            "price_change": 0,
            "avg_volume": 0,
            "volatility": 0,
            "trend": "No data available"
        }
    
    latest = history.iloc[-1]
    oldest = history.iloc[0]
    
    # Calculate metrics
    price_change = ((latest['Close'] - oldest['Close']) / oldest['Close']) * 100
    avg_volume = history['Volume'].mean()
    volatility = history['Close'].std()
    
    # Determine trend
    if price_change > 10:
        trend = "strong upward 📈"
    elif price_change > 0:
        trend = "slight upward ↗️"
    elif price_change > -10:
        trend = "slight downward ↘️"
    else:
        trend = "significant downward 📉"
    
    return {
        "price_change": price_change,
        "avg_volume": avg_volume,
        "volatility": volatility,
        "trend": trend
    }



def generate_local_insights(stock_data, trends):
    if "error" in stock_data:
        return f"❌ Error fetching stock data: {stock_data['error']}"

    current_price = stock_data.get('current_price', 'N/A')
    price_change = trends.get('price_change', 0)
    trend = trends.get('trend', 'No clear trend')
    pe_ratio = stock_data.get('pe_ratio', 'N/A')
    low_52w = stock_data.get('low_52w', 'N/A')
    high_52w = stock_data.get('high_52w', 'N/A')

    if price_change > 10:
        direction = 'strong upward momentum'
    elif price_change > 0:
        direction = 'a gentle upward trend'
    elif price_change > -10:
        direction = 'a slight downward movement'
    else:
        direction = 'a sharper downward trend'

    risk_note = 'It appears relatively stable for a beginner' if abs(price_change) < 10 and (pe_ratio == 'N/A' or (isinstance(pe_ratio, (int, float)) and pe_ratio < 30)) else 'It may be somewhat riskier, so proceed cautiously'

    return (
        f"Over the past 6 months, {stock_data.get('name', stock_data.get('symbol', 'this stock'))} shows {direction} ({price_change:.1f}%). "
        f"The current price is ₹{current_price}, with a 52-week range of ₹{low_52w} to ₹{high_52w}. "
        f"Based on this data, {risk_note}. "
        f"For a beginner, consider watching the trend and avoiding large positions until the stock shows more consistency."
    )


def generate_local_insights(stock_data, trends, indicators=None, prefs=None):
    """Local insight generator that considers EMA and RSI plus user prefs.
    indicators: dict with keys 'ema_short', 'ema_long', 'rsi'
    prefs: dict with user preferences like 'risk_profile' and 'insight_style'
    """
    if "error" in stock_data:
        return f"❌ Error fetching stock data: {stock_data['error']}"

    name = stock_data.get('name', stock_data.get('symbol', 'this stock'))
    price_change = trends.get('price_change', 0)

    ema_short = indicators.get('ema_short') if indicators else None
    ema_long = indicators.get('ema_long') if indicators else None
    rsi = indicators.get('rsi') if indicators else None

    # EMA signal
    ema_signal = None
    if ema_short is not None and ema_long is not None:
        if ema_short > ema_long:
            ema_signal = 'bullish (short EMA above long EMA)'
        elif ema_short < ema_long:
            ema_signal = 'bearish (short EMA below long EMA)'
        else:
            ema_signal = 'neutral (EMAs are close)'

    # RSI signal
    rsi_signal = None
    if rsi is not None:
        if rsi > 70:
            rsi_signal = 'overbought (RSI > 70)'
        elif rsi < 30:
            rsi_signal = 'oversold (RSI < 30)'
        else:
            rsi_signal = 'neutral'

    # Personalization
    risk = (prefs.get('risk_profile') if prefs else 'Balanced')
    style = (prefs.get('insight_style') if prefs else 'Concise')

    # Compose base message
    parts = []
    parts.append(f"{name} shows {trends.get('trend', 'no clear trend')} over the last 6 months ({price_change:.1f}%).")
    if ema_signal:
        parts.append(f"Technicals: {ema_signal}.")
    if rsi_signal:
        parts.append(f"Momentum: {rsi_signal} (RSI {rsi:.1f}).")

    # Risk-adjusted recommendation
    if risk == 'Conservative':
        parts.append("Recommendation: Consider small positions or wait for clearer confirmation due to risk aversion.")
    elif risk == 'Aggressive':
        parts.append("Recommendation: You may consider buying on pullbacks, but manage position size and stops.")
    else:
        parts.append("Recommendation: Monitor the EMAs and RSI; consider entering on confirmation.")

    message = " ".join(parts)
    if style == 'Concise':
        # Return first two sentences for concise mode
        return " ".join(message.split('.')[:2]).strip() + '.'
    return message


def generate_insights(client, stock_data, trends, indicators=None, prefs=None):
    """Use OpenAI if available, otherwise local insights. Both consider indicators and prefs."""
    if "error" in stock_data:
        return f"❌ Error fetching stock data: {stock_data['error']}"

    if not client:
        return generate_local_insights(stock_data, trends, indicators=indicators, prefs=prefs)

    # Build prompt including indicators and user preferences
    ema_short = indicators.get('ema_short') if indicators else None
    ema_long = indicators.get('ema_long') if indicators else None
    rsi = indicators.get('rsi') if indicators else None
    risk = prefs.get('risk_profile') if prefs else 'Balanced'
    horizon = prefs.get('horizon') if prefs else 'Medium'

    prompt = f"""You are a friendly, concise stock analyst writing for a beginner.

Stock: {stock_data.get('name', 'Unknown')} ({stock_data.get('symbol')})
Current Price: ₹{stock_data.get('current_price', 'N/A')}
6-Month Trend: {trends.get('trend', 'N/A')}
Price Change (6m): {trends.get('price_change', 0):.1f}%

Indicators:
- EMA short: {ema_short}
- EMA long: {ema_long}
- RSI: {rsi}

User preferences:
- Risk profile: {risk}
- Investment horizon: {horizon}

Task: Considering the trend and the indicators above, provide a short (2-3 sentences) explanation:
1) What the indicators suggest (mention EMA crossover and RSI levels).
2) Whether this stock seems risky or stable for the given risk profile.
3) A practical, risk-adjusted recommendation for a beginner with the stated horizon.

Be concise and avoid speculative price targets. If indicators conflict, explain the conflict and recommend a cautious approach.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=220,
            temperature=0.6
        )
        return response.choices[0].message.content
    except Exception:
        return generate_local_insights(stock_data, trends, indicators=indicators, prefs=prefs)


# UI Layout
st.title("📈 StockLens")
st.subheader("AI-Powered Stock Insights in Simple Language")

# Input section
stock_symbol = st.text_input(
    "Enter Stock Symbol",
    placeholder="e.g., RELIANCE, TCS, AAPL, MSFT",
    help="Enter the stock ticker symbol (NSE: RELIANCE, BSE: 500325, US: AAPL)",
    key='stock_input'
)
stock_symbol = (stock_symbol or '').strip().upper()

if stock_symbol:
    with st.spinner("Fetching stock data..."):
        # Fetch data
        stock_data = fetch_stock_data(stock_symbol)
        
        if "error" in stock_data:
            st.error(f"Could not find stock: {stock_data['error']}")
            st.info("💡 Try symbols like: RELIANCE, TCS, INFY, HDFCBANK, AAPL, MSFT")
        else:
            # Display stock info
            st.success(f"Found: {stock_data.get('name', stock_symbol)}")
            
            # Metrics row
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Price", f"₹{stock_data.get('current_price', 'N/A')}")
            with col2:
                st.metric("P/E Ratio", f"{stock_data.get('pe_ratio', 'N/A')}")
            with col3:
                st.metric("Volume", f"{stock_data.get('volume', 'N/A'):,.0f}" if isinstance(stock_data.get('volume'), (int, float)) else "N/A")
            
            # Analyze trends
            trends = analyze_trends(stock_data.get('history'))

            # Price chart (6 months) + technical indicators
            st.subheader("📈 Price Chart (6 months)")
            hist = stock_data.get('history')
            if hist is not None and not hist.empty:
                hist = hist.copy()
                # Ensure the index is a column for Altair
                hist.reset_index(inplace=True)

                # Calculate EMAs using sidebar periods
                ema_short_period = int(st.session_state.get('ema_short', 20))
                ema_long_period = int(st.session_state.get('ema_long', 50))
                rsi_period = int(st.session_state.get('rsi_period', 14))

                hist['EMA_short'] = hist['Close'].ewm(span=ema_short_period, adjust=False).mean()
                hist['EMA_long'] = hist['Close'].ewm(span=ema_long_period, adjust=False).mean()

                # RSI
                def compute_rsi(series, period=14):
                    delta = series.diff()
                    gain = delta.where(delta > 0, 0.0)
                    loss = -delta.where(delta < 0, 0.0)
                    # Use Wilder's smoothing with exponential moving average
                    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
                    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
                    rs = avg_gain / avg_loss
                    rsi = 100 - (100 / (1 + rs))
                    return rsi.fillna(0)

                hist['RSI'] = compute_rsi(hist['Close'], rsi_period)

                # Show latest indicator values
                latest = hist.iloc[-1]
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric(f"EMA {ema_short_period}", f"₹{latest['EMA_short']:.2f}")
                with col_b:
                    st.metric(f"EMA {ema_long_period}", f"₹{latest['EMA_long']:.2f}")
                with col_c:
                    st.metric(f"RSI ({rsi_period})", f"{latest['RSI']:.1f}")

                # Save symbol button
                if st.button("Save symbol"):
                    s = stock_symbol
                    if s and s not in st.session_state['saved_symbols']:
                        st.session_state['saved_symbols'].append(s)
                        st.success(f"Saved {s}")

                # Price + EMA chart (Altair)
                base = alt.Chart(hist).encode(x=alt.X('Date:T', title='Date'))

                price_line = base.mark_line(color='#1f77b4').encode(y=alt.Y('Close:Q', title='Price'))
                ema_short_line = base.mark_line(color='#ff7f0e').encode(y='EMA_short:Q')
                ema_long_line = base.mark_line(color='#2ca02c').encode(y='EMA_long:Q')

                price_chart = alt.layer(price_line, ema_short_line, ema_long_line).properties(height=300)
                price_chart = price_chart.encode(tooltip=['Date:T', 'Close:Q', 'EMA_short:Q', 'EMA_long:Q'])

                # RSI chart with overbought/oversold lines
                rsi_chart = alt.Chart(hist).mark_line(color='#9467bd').encode(
                    x='Date:T',
                    y=alt.Y('RSI:Q', title=f'RSI ({rsi_period})')
                ).properties(height=120)

                overbought = alt.Chart(hist).mark_rule(color='red', strokeDash=[5,5]).encode(y=alt.value(70))
                oversold = alt.Chart(hist).mark_rule(color='green', strokeDash=[5,5]).encode(y=alt.value(30))

                combined = alt.vconcat(price_chart, (rsi_chart + overbought + oversold)).resolve_scale(x='shared')

                st.altair_chart(combined, use_container_width=True)
            else:
                st.info("No historical data available for chart.")

            st.divider()

            # AI Insights
            st.subheader("🤖 AI Insight")
            
            client = get_openai_client()

            # Prepare indicators and prefs for insights
            indicators = None
            prefs = {
                'risk_profile': st.session_state.get('risk_profile', 'Balanced'),
                'horizon': st.session_state.get('horizon', 'Medium'),
                'insight_style': st.session_state.get('insight_style', 'Concise')
            }
            if hist is not None and not hist.empty:
                indicators = {
                    'ema_short': float(latest.get('EMA_short')) if 'EMA_short' in latest else None,
                    'ema_long': float(latest.get('EMA_long')) if 'EMA_long' in latest else None,
                    'rsi': float(latest.get('RSI')) if 'RSI' in latest else None
                }

            insights = generate_insights(client, stock_data, trends, indicators=indicators, prefs=prefs)
            st.write(insights)
            
            # Technical details (expandable)
            with st.expander("📊 Technical Details"):
                st.write(f"**Trend:** {trends.get('trend', 'N/A')}")
                st.write(f"**6-Month Price Change:** {trends.get('price_change', 0):.1f}%")
                st.write(f"**52-Week Range:** ₹{stock_data.get('low_52w', 'N/A')} - ₹{stock_data.get('high_52w', 'N/A')}")
                st.write(f"**Market Cap:** {stock_data.get('market_cap', 'N/A'):,.0f}" if isinstance(stock_data.get('market_cap'), (int, float)) else "N/A")

else:
    st.info("👆 Enter a stock symbol above to get started!")
    st.markdown("""
    **Popular Stocks to Try:**
    - Indian: RELIANCE, TCS, INFY, HDFCBANK, SBIN
    - US: AAPL, MSFT, GOOGL, AMZN, TSLA
    """)