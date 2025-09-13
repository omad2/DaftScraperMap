import argparse
import sys
from loguru import logger
from core import DaftScraper
from config import config

def setup_logging():
    """Setup logging configuration"""
    logger.remove()  # Remove default handler
    logger.add(
        sys.stdout,
        level=config.LOG_LEVEL,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    logger.add(
        "logs/daft_scraper.log",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="10 MB",
        retention="7 days"
    )

def main():
    """Main function - Interactive Property Scraper"""
    parser = argparse.ArgumentParser(description="DublinMap Interactive Property Scraper")
    parser.add_argument(
        "--interactive",
        action="store_true",
        default=True,
        help="Use interactive mode (default behavior)"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging()
    
    logger.info("🏠 DublinMap Property Scraper - Interactive Mode")
    logger.info("=" * 50)
    
    # Validate Supabase configuration
    if not config.SUPABASE_URL or not config.SUPABASE_KEY:
        logger.error("❌ SUPABASE_URL and SUPABASE_KEY environment variables are required")
        sys.exit(1)
    
    try:
        # Initialize scraper
        scraper = DaftScraper()
        
        # Always use interactive mode
        result = scraper.interactive_scrape("dublin")
        
        # Log results
        if result["success"]:
            logger.success(f"✅ Scraping completed successfully: {result['message']}")
            if "details" in result:
                for listing_type, details in result["details"].items():
                    logger.info(f"📊 {listing_type.title()}: {details['count']} properties")
        else:
            logger.error(f"❌ Scraping failed: {result['message']}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("⏹️ Scraping interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"💥 Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
