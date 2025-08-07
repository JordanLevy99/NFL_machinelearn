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
import pandas as pd
import json

from NFL_machinelearn.data.downloaders.ff_today_downloader import FFTodayDownloader
from NFL_machinelearn.ml.models.nfl_predictor import NFLPredictor, ModelConfig
from NFL_machinelearn.data.data_manager import DataManager
from NFL_machinelearn.data.processors import DataProcessor
from NFL_machinelearn.utils.browser_setup import create_chrome_driver

def setup_logging(log_level: str) -> None:
    """Configure logging for the training process."""
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
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
    downloader: Optional[FFTodayDownloader],
    data_manager: DataManager,
    data_processor: DataProcessor,
    start_year: int,
    end_year: int,
    force_download: bool = False
) -> None:
    """Train a model for a specific position.
    
    Args:
        position: Player position (QB, RB, WR, TE)
        downloader: FFToday downloader instance (optional)
        data_manager: Data manager instance
        data_processor: Data processor instance
        start_year: Start year for training data
        end_year: End year for training data
        force_download: Whether to force data download even if it exists
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Check which files need to be downloaded
        missing_files = data_manager.check_data_exists(start_year, end_year, position)
        
        if downloader and (force_download or missing_files):
            logger.info(f"Downloading data for {position}")
            if force_download:
                # Download all data if force download is requested
                downloader.download_year_range([position], start_year, end_year, data_manager.raw_data_dir)
            else:
                # Download only missing files
                for year, missing_types in missing_files.items():
                    logger.info(f"Downloading {position} {year} data: {', '.join(missing_types)}")
                    for data_type in missing_types:
                        if data_type == 'projected':
                            downloader.download_position_data(position, year, data_manager.raw_data_dir / str(year))
                        else:  # actual
                            downloader.download_year_range([position], year, year, data_manager.raw_data_dir)
        
        # Process training data
        logger.info(f"Processing data for {position}")
        training_data = data_processor.process_training_data(position, start_year, end_year)
        
        # Get test data for current year
        testing_data = data_manager.load_position_data(end_year, position, "projected")
        
        # Train model
        logger.info(f"Training model for {position}")
        logger.debug(f"Columns of training data: {training_data.columns.tolist()}")
        logger.debug(f"Columns of testing data: {testing_data.columns.tolist()}")
        
        # Drop year and GP columns from training data as they shouldn't be used for prediction
        columns_to_drop = ['Yr', 'GP', 'GP_projected', 'GP_actual']
        training_data = training_data.drop(columns=[col for col in columns_to_drop if col in training_data.columns])
        
        # Create model configuration
        model_config = ModelConfig(
            hidden_layers=[100],  # Single hidden layer with 100 neurons
            activation='relu',
            alpha=0.001,
            max_iter=300,
            validation_fraction=0.2,
            early_stopping=True
        )
        
        # Initialize and train predictor
        predictor = NFLPredictor(model_config)
        
        # Preprocess training data
        train_processed, feature_cols = predictor.preprocess_data(training_data)
        X_train = train_processed[feature_cols]
        y_train = train_processed['Act FPts']
        
        # Train model and get metrics
        metrics = predictor.train(X_train, y_train)
        logger.info(f"Model metrics: MSE={metrics.mse:.2f}, RMSE={metrics.rmse:.2f}, R2={metrics.r2:.2f}")
        
        # Rename test data columns to match training data format
        column_mapping = {}
        for col in testing_data.columns:
            if col not in ['Name', 'Team']:
                column_mapping[col] = f"{col}_projected"
        testing_data = testing_data.rename(columns=column_mapping)
        
        # Preprocess and predict on test data
        test_processed, _ = predictor.preprocess_data(testing_data)
        X_test = test_processed[feature_cols]
        predictions = predictor.predict(X_test)
        
        # Save predictions
        output_dir = Path('data') / 'ML_projections' / str(end_year)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        predictions_df = pd.DataFrame({
            'Player': testing_data['Name'],
            'Projection': testing_data['FPts_projected'],
            'My Computed Score': predictions
        })
        
        output_file = output_dir / f"{position}_{end_year}_0.csv"
        predictions_df.to_csv(output_file, index=False)
        
        # Save both model and metrics
        model_dir = Path('data') / 'models' / str(end_year)
        model_dir.mkdir(parents=True, exist_ok=True)
        
        # Save model
        model_path = model_dir / f"{position}_model.joblib"
        predictor.save_model(model_path)
        
        # Save metrics alongside model
        metrics_path = model_dir / f"{position}_metrics.json"
        metrics_dict = {
            'mse': float(metrics.mse),
            'rmse': float(metrics.rmse),
            'r2': float(metrics.r2),
            'training_date': pd.Timestamp.now().isoformat(),
            'model_config': model_config.__dict__,
            'feature_columns': feature_cols
        }
        
        with open(metrics_path, 'w') as f:
            json.dump(metrics_dict, f, indent=4)
            
        logger.info(f"Model and metrics saved to {model_dir}")
        
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
    parser.add_argument('--log-level', type=str, choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                      default='INFO', help='Set the logging level')
    args = parser.parse_args()
    
    setup_logging(args.log_level)
    setup_environment()
    logger = logging.getLogger(__name__)
    
    # Initialize managers and processors
    data_dir = Path('data')
    data_manager = DataManager(data_dir)
    data_processor = DataProcessor(data_dir / 'raw')
    
    # Check if we need to download any data
    need_download = args.force_download
    missing_data = {}
    if not need_download:
        for position in args.positions:
            missing = data_manager.check_data_exists(args.start_year, args.end_year, position)
            if missing:
                need_download = True
                missing_data[position] = missing
                logger.info(f"Missing data for {position}:")
                for year, types in missing.items():
                    logger.info(f"  {year}: {', '.join(types)}")
    
    driver = None
    downloader = None
    
    try:
        if need_download:
            logger.info("Initializing Chrome driver for data download...")
            driver = create_chrome_driver(args.chrome_driver)
            downloader = FFTodayDownloader(driver)
            login_to_fftoday(driver)
        else:
            logger.info("All required data exists. Skipping data download.")
        
        # Train models for each position
        for position in args.positions:
            try:
                logger.info(f"Starting training process for {position}")
                train_position_model(
                    position,
                    downloader,
                    data_manager,
                    data_processor,
                    args.start_year,
                    args.end_year,
                    args.force_download
                )
            except Exception as e:
                logger.error(f"Error training {position} model: {str(e)}")
                continue
                
    finally:
        if driver:
            driver.quit()

if __name__ == '__main__':
    main() 