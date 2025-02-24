"""
Configuration module for Deep Researcher
"""

import os
from dataclasses import dataclass
from typing import List


@dataclass
class Config:
    """Configuration class for Deep Researcher"""
    
    # LLM configuration
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "mistral"
    reasoning_model: str = "deepseek-r1"  # Advanced model for complex reasoning
    
    # Browser configuration
    headless: bool = False
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
    
    # Timeout settings
    page_load_timeout: int = 30
    script_timeout: int = 30
    
    # Output settings
    output_dir: str = "output"
    
    # Sites that often block web scraping
    blocked_sites: List[str] = None
    
    def __post_init__(self):
        """Initialize default values after dataclass initialization"""
        if self.blocked_sites is None:
            self.blocked_sites = [
                'msn.com',
                'facebook.com',
                'sfgate.com',
                'nytimes.com',
                'medium.com',
                'wsj.com',
                'bloomberg.com'
            ]
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
