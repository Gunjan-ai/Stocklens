# StockLens Configuration
# Add your OpenAI API key here

# StockLens Configuration
# Prefer loading the OpenAI API key from the environment (.env) to avoid committing secrets.
import os

# Load from environment variable set in .env or the shell
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# For convenience you can still set a key here (NOT recommended):
# OPENAI_API_KEY = "your_api_key_here"

