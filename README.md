# AI Stock Insight Assistant
Streamlit + OpenAI + yfinance

## Setup
```bash
pip install -r requirements.txt
streamlit run app.py
```

## OpenAI API Key (Optional)
This app can run without an OpenAI API key by using built-in local analysis. If you do have a key and want AI-generated text, create a `.env` file:
```
OPENAI_API_KEY=your_api_key_here
```

## Features
- Enter any stock name (Reliance, TCS, Apple, etc.)
- Fetches real-time stock data
- Analyzes price trends
- Generates AI-powered insights in simple language