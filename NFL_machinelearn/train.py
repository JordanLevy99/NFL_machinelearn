import logging
import argparse
import os
from pathlib import Path
from typing import List, Optional
import subprocess
import requests
from dotenv import load_dotenv
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver

from NFL_machinelearn.data.downloaders.ff_today_downloader import FFTodayDownloader
from NFL_machinelearn.ml.models.train_model import (
    merging_proj_with_actual,
    gp_stats_adjuster,
    machine_learning,
    dataframe_creator
)
from NFL_machinelearn.data.data_manager import DataManager
from NFL_machinelearn.utils.browser_setup import create_chrome_driver

def setup_logging() -> None:
    """Configure logging for the training process."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def get_chromedriver_path() -> str:
    """Get the ChromeDriver path."""
    local_path = Path('drivers/chromedriver').absolute()
    if local_path.exists():
        return str(local_path)
    try:
        result = subprocess.run(['which', 'chromedriver'], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return str(local_path)

def setup_environment() -> None:
    """Load environment variables from .env file."""
    load_dotenv()
    if not all([os.getenv('FFTODAY_USERNAME'), os.getenv('FFTODAY_PASSWORD')]):
        raise ValueError("Missing FFToday credentials in .env file")

def login_to_fftoday(driver: webdriver.Chrome) -> None:
    """Automatically log in to FFToday using credentials from .env file.
    
    Args:
        driver: Selenium WebDriver instance
    """
    logger = logging.getLogger(__name__)
    wait = WebDriverWait(driver, 10)
    
    try:
        driver.get('http://www.fftoday.com/oss8/users/login.php?ce=0&group=39&url=www.fftoday.com/members/%3fr=playerproj')
        
        # Wait for and fill in username
        username_field = wait.until(EC.presence_of_element_located((By.NAME, "username")))
        username_field.send_keys(os.getenv('FFTODAY_USERNAME'))
        
        # Fill in password
        password_field = driver.find_element(By.NAME, "password")
        password_field.send_keys(os.getenv('FFTODAY_PASSWORD'))

        # Click login button
        login_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        login_button.click()
        
        # Wait for successful login (adjust the selector based on FFToday's post-login page)
        wait.until(EC.url_contains("rankings"))
        logger.info("Successfully logged in to FFToday")
        
    except Exception as e:
        logger.error(f"Failed to log in to FFToday: {str(e)}")
        raise

def train_position_model(
    position: str,
    downloader: FFTodayDownloader,
    start_year: int,
    end_year: int,
    force_download: bool = False
) -> None:
    """Train a model for a specific position.
    
    Args:
        position: Player position (QB, RB, WR, TE)
        downloader: FFToday downloader instance
        start_year: Start year for training data
        end_year: End year for training data
        force_download: Whether to force data download even if it exists
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Set up data directories
        data_dir = Path('data')
        data_manager = DataManager(data_dir)
        
        # Download data if forced or if data doesn't exist
        if force_download or not data_manager.check_data_exists(start_year, end_year, position):
            logger.info(f"Downloading data for {position}")
            # Download historical data
            downloader.download_year_range([position], start_year, end_year, data_manager.raw_data_dir)
            # Download test data 
            downloader.download_position_data(position, end_year, data_manager.raw_data_dir / str(end_year))
        
        # Load and process data
        logger.info(f"Processing data for {position}")
        training_data = data_manager.load_training_data(start_year, end_year, position)
        
        # Adjust for games played
        training_data = gp_stats_adjuster(training_data)
        
        # Get test data for current year
        testing_data = data_manager.load_position_data(end_year, position, "projected")
        
        # Train model
        logger.info(f"Training model for {position}")
        machine_learning(training_data, testing_data, position, end_year, 0)
        
        logger.info(f"Completed training for {position}")
        
    except Exception as e:
        logger.error(f"Error training {position} model: {str(e)}")
        raise

def main():
    parser = argparse.ArgumentParser(description='Train NFL player prediction models')
    parser.add_argument('--positions', nargs='+', default=['QB', 'RB', 'WR', 'TE'],
                      help='Positions to train models for')
    parser.add_argument('--start-year', type=int, default=2018,
                      help='Start year for training data')
    parser.add_argument('--end-year', type=int, default=2023,
                      help='End year for training data')
    parser.add_argument('--force-download', action='store_true',
                      help='Force download of data even if it exists')
    parser.add_argument('--chrome-driver', type=str,
                      default=get_chromedriver_path(),
                      help='Path to ChromeDriver')
    args = parser.parse_args()
    
    setup_logging()
    setup_environment()
    logger = logging.getLogger(__name__)
    
    # Initialize Chrome driver with adblock
    driver = create_chrome_driver(args.chrome_driver)
    
    try:
        # Initialize downloader
        downloader = FFTodayDownloader(driver)
        
        # Replace manual login with automatic login
        login_to_fftoday(driver)
        
        # Train models for each position
        for position in args.positions:
            try:
                logger.info(f"Starting training process for {position}")
                train_position_model(
                    position,
                    downloader,
                    args.start_year,
                    args.end_year,
                    args.force_download
                )
            except Exception as e:
                logger.error(f"Error training {position} model: {str(e)}")
                continue
                
    finally:
        driver.quit()

if __name__ == '__main__':
    main() 