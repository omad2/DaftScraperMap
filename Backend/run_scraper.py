#!/usr/bin/env python3
"""
Main entry point for DublinMap Scraper
"""

import sys
import os

# Add the Backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import main

if __name__ == "__main__":
    main()
