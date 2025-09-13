import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Daft.ie configuration
    DAFT_BASE_URL = os.getenv('DAFT_BASE_URL', 'https://www.daft.ie')
    
    # Scraping configuration
    MAX_PAGES_TO_FETCH = int(os.getenv('MAX_PAGES_TO_FETCH', '5'))
    MAX_FETCH_RETRIES = int(os.getenv('MAX_FETCH_RETRIES', '2'))
    RETRY_DELAY_MS = int(os.getenv('RETRY_DELAY_MS', '2000'))
    REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '10000'))
    USER_AGENT = os.getenv('USER_AGENT', 
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36')
    
    # Supabase configuration
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')
    
    # Logging configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

config = Config()
