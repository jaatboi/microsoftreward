#!/usr/bin/env python3
"""
Configuration and utility functions for the AI Search Agent.
"""

import os
from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class SearchConfig:
    """Configuration dataclass for search parameters."""
    gemini_api_key: str = "GEMINI_API_KEY"
    edge_driver_path: str = "auto"
    debug_mode: bool = False
    log_level: str = "INFO"
    max_cycles: int = 54
    min_delay: int = 10
    max_delay: int = 59
    
    @classmethod
    def from_env(cls) -> 'SearchConfig':
        """Create config from environment variables."""
        return cls(
            gemini_api_key=os.getenv('GEMINI_API_KEY', 'GEMINI_API_KEY'),
            edge_driver_path=os.getenv('EDGE_DRIVER_PATH', 'auto'),
            debug_mode=os.getenv('DEBUG_MODE', 'False').lower() == 'true',
            log_level=os.getenv('LOG_LEVEL', 'INFO'),
            max_cycles=int(os.getenv('MAX_SEARCH_CYCLES', '54')),
            min_delay=int(os.getenv('MIN_DELAY', '10')),
            max_delay=int(os.getenv('MAX_DELAY', '59'))
        )


def validate_environment() -> Dict[str, Any]:
    """Validate environment setup and dependencies."""
    issues = []
    
    # Check API key
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key or api_key == 'your_gemini_api_key_here':
        issues.append("GEMINI_API_KEY not properly set in .env file")
    
    # Check required packages
    required_packages = [
        'selenium', 'google.generativeai', 'colorama', 
        'pandas', 'fake_useragent', 'dotenv', 'webdriver_manager'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        issues.append(f"Missing packages: {', '.join(missing_packages)}")
    
    return {
        'valid': len(issues) == 0,
        'issues': issues,
        'api_key_set': bool(api_key and api_key != 'your_gemini_api_key_here')
    }


def setup_directories():
    """Create necessary directories for logs and data."""
    directories = ['logs', 'data', 'reports']
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)


if __name__ == "__main__":
    # Quick environment check
    result = validate_environment()
    print(f"Environment valid: {result['valid']}")
    if result['issues']:
        print("Issues found:")
        for issue in result['issues']:
            print(f"  - {issue}")