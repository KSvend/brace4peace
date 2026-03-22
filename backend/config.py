"""Configuration from environment variables."""
import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
# Use service role key for the pilot — anon key rejected by supabase-py with newer key format
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ["SUPABASE_KEY"]
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
API_KEY = os.environ.get("B4P_API_KEY") or os.environ.get("API_KEY", "")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
