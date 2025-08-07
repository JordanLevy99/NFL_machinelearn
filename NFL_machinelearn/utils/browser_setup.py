"""Browser setup and configuration utilities."""

import logging
import os
from pathlib import Path
import requests
import zipfile
import io
import shutil
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

logger = logging.getLogger(__name__)

def setup_chrome_options() -> Options:
    """Configure Chrome options for web scraping.
    
    Returns:
        Configured Chrome options
    """
    chrome_options = Options()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-software-rasterizer')
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--allow-running-insecure-content')
    chrome_options.add_argument('--window-size=1920,1080')
    
    return chrome_options

def setup_adblock(chrome_options: Options) -> Options:
    """Add uBlock Origin extension to Chrome options.
    
    Args:
        chrome_options: Chrome options to add the extension to
        
    Returns:
        Updated Chrome options with adblock extension
    """
    extensions_dir = Path('extensions').absolute()
    ublock_dir = extensions_dir / 'uBlock0.chromium'
    
    if not (ublock_dir / 'manifest.json').exists():
        logger.info("Downloading and extracting uBlock Origin extension...")
        
        # Create extensions directory if it doesn't exist
        os.makedirs(extensions_dir, exist_ok=True)
        
        # Clean up any existing files
        if ublock_dir.exists():
            shutil.rmtree(ublock_dir)
        
        # Download uBlock Origin extension
        ublock_url = "https://github.com/gorhill/uBlock/releases/download/1.55.0/uBlock0_1.55.0.chromium.zip"
        response = requests.get(ublock_url)
        
        # Extract the extension
        with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
            zip_ref.extractall(extensions_dir)
            
        logger.info("uBlock Origin extension extracted successfully")
        
        # Verify manifest exists
        if not (ublock_dir / 'manifest.json').exists():
            logger.error("Failed to find manifest.json in extracted extension")
            raise FileNotFoundError("manifest.json not found in uBlock Origin extension")
    
    chrome_options.add_argument(f'--load-extension={ublock_dir}')
    return chrome_options

def create_chrome_driver(chrome_driver_path: str) -> webdriver.Chrome:
    """Create a configured Chrome WebDriver instance.
    
    Args:
        chrome_driver_path: Path to ChromeDriver executable
        
    Returns:
        Configured Chrome WebDriver instance
    """
    chrome_options = setup_chrome_options()
    chrome_options = setup_adblock(chrome_options)
    
    service = Service(executable_path=chrome_driver_path)
    return webdriver.Chrome(service=service, options=chrome_options) 