#!/usr/bin/env python3
"""
Startup script for DublinMap API server
"""

import uvicorn
import sys
import os
from loguru import logger
from config import config

def setup_logging():
    """Setup logging configuration for API"""
    logger.remove()  # Remove default handler
    logger.add(
        sys.stdout,
        level=config.LOG_LEVEL,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    logger.add(
        "logs/api.log",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="10 MB",
        retention="7 days"
    )

def main():
    """Main function to start the API server"""
    # Setup logging
    setup_logging()
    
    # Validate configuration
    if not config.SUPABASE_URL or not config.SUPABASE_KEY:
        logger.error("SUPABASE_URL and SUPABASE_KEY environment variables are required")
        sys.exit(1)
    
    logger.info("Starting DublinMap API server...")
    logger.info(f"Configuration: LOG_LEVEL={config.LOG_LEVEL}")
    
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Start the server
    try:
        uvicorn.run(
            "api.api:app",
            host="0.0.0.0",
            port=8000,
            reload=False,  # Set to True for development
            log_level=config.LOG_LEVEL.lower(),
            access_log=True
        )
    except KeyboardInterrupt:
        logger.info("API server stopped by user")
    except Exception as e:
        logger.error(f"Failed to start API server: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
