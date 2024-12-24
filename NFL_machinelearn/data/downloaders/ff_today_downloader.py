from pathlib import Path
import time
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from typing import Dict, List, Optional
from io import StringIO
import logging

from .base_downloader import BaseDownloader
from NFL_machinelearn.config.config import CONFIG

class FFTodayDownloader(BaseDownloader):
    """Downloads NFL player data from FFToday.com."""
    
    def __init__(self, driver: webdriver.Chrome):
        """Initialize the FFToday downloader."""
        super().__init__()
        self.driver = driver
        self.base_url = CONFIG['BASE_URL']
        self.positions = CONFIG['POSITIONS']
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
    
    def _debug_df_info(self, df: pd.DataFrame, stage: str) -> None:
        """Print debug information about a DataFrame."""
        self.logger.debug(f"\n{'='*20} {stage} {'='*20}")
        self.logger.debug(f"Shape: {df.shape}")
        self.logger.debug(f"Columns: {df.columns.tolist()}")
        if len(df) > 0:
            self.logger.debug(f"Sample data (first 2 rows):\n{df.head(2)}")
    
    def _process_table(self, table: pd.DataFrame, position: str, data_type: str, year: int) -> pd.DataFrame:
        """Process a raw table from FFToday into a clean DataFrame.
        
        Args:
            table: Raw DataFrame from website
            position: Player position
            data_type: Type of data (projected or actual)
            year: Year of data
            
        Returns:
            Processed DataFrame
        """
        try:
            # Skip empty or header-only rows
            df = table.copy()
            df = df[~df.iloc[:, 1].isna()]  # Remove rows where first column is NaN
            df = df[df.iloc[:, 0] != 'Chg']  # Remove header row
            if data_type == 'projected':
                df = df.drop(columns=[0])  # Drop first column
            # map column based on config
            if data_type == 'actual':
                df.columns = df.iloc[0]
                df = df.iloc[1:]
            df = df.drop(columns=CONFIG['DROP_COLUMNS'][data_type][position])
            if len(df.columns) == len(CONFIG['DOWNLOAD_COLUMNS'][data_type][position]):
                df.columns = CONFIG['DOWNLOAD_COLUMNS'][data_type][position]
            else:
                raise ValueError(f"Column mismatch for {position} {data_type}: {len(df.columns)} columns found")

            
            # Check for required columns
            required_cols = ['Name', 'Team', 'FPts']
            if data_type == 'actual':
                required_cols.append('GP')
                
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                self.logger.error(f"Missing columns in {data_type} data: {missing_cols}")
                self.logger.debug(f"Available columns: {df.columns.tolist()}")
                raise ValueError(f"Missing required columns for {position}: {missing_cols}")
            
            # Add GP column for projected data if missing
            if data_type == 'projected' and 'GP' not in df.columns:
                games_in_season = 17 if year >= 2021 else 16
                df['GP'] = games_in_season
                self.logger.info(f"Added default GP={games_in_season} for projected data")
            
            # Clean up data
            df = df.replace('--', '0')  # Replace '--' with '0'
            for col in df.columns:
                if col not in ['Name', 'Team', 'Change', 'Bye']:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Clean up player names (remove ranking numbers)
            df['Name'] = df['Name'].str.extract(r'(?:\d+\.\s+)?(.+)')[0]
            
            # Remove rows with missing values in required columns
            df = df.dropna(subset=required_cols)
            
            self.logger.debug(f"Final DataFrame shape for {position} {data_type}: {df.shape}")
            self.logger.debug(f"Final DataFrame columns for {position} {data_type}: {df.columns.tolist()}")
            if len(df) > 0:
                self.logger.debug(f"First record in final DataFrame: {df.iloc[0].to_dict()}")
            
            return df
            
        except Exception as e:
            self.logger.warning(f"Error processing table: {str(e)}")
            return pd.DataFrame()
    
    def download_position_data(self, position: str, year: int, save_dir: Path) -> None:
        """Download data for a specific position and year."""
        if position not in self.positions:
            raise ValueError(f"Invalid position: {position}")
            
        position_info = self.positions[position]
        
        # Ensure save directory exists
        self.ensure_directory(save_dir)
        
        # Download both projected and actual data
        for data_type in ['projected', 'actual']:
            try:
                self.logger.info(f"Starting {data_type} data download for {position} {year}")
                
                all_data = []
                for page in range(position_info['pages']):
                    # Construct URL based on data type
                    if data_type == 'projected':
                        url = f"{self.base_url}/rankings/playerproj.php?&PosID={position_info['id']}&Season={year}&LeagueID={CONFIG['LEAGUE_ID']}&cur_page={page}"
                    else:
                        url = f"{self.base_url}/stats/playerstats.php?Season={year}&PosID={position_info['id']}&LeagueID={CONFIG['LEAGUE_ID']}&cur_page={page}&ShowG=Y"
                    
                    self.logger.debug(f"Attempting to download {data_type} data for {position} from URL: {url}")
                    
                    # Get page data
                    page_data = self._download_page(url, position, data_type, year)
                    if page_data is not None:
                        self.logger.debug(f"Successfully downloaded {len(page_data)} records from page {page}")
                        self.logger.debug(f"Sample record from page {page}: {page_data[0] if page_data else None}")
                        all_data.extend(page_data)
                    else:
                        self.logger.warning(f"No data found on page {page} for {position} {data_type}")
                    
                    time.sleep(1)  # Be nice to the server
                
                # Save data
                if all_data:
                    save_path = save_dir / f"{position}_{data_type}.csv"
                    
                    # Convert to DataFrame
                    df = pd.DataFrame(all_data)
                    self.logger.debug(f"Final DataFrame shape for {position} {data_type}: {df.shape}")
                    self.logger.debug(f"Final DataFrame columns for {position} {data_type}: {df.columns.tolist()}")
                    self.logger.debug(f"First record in final DataFrame: {df.iloc[0].to_dict() if len(df) > 0 else None}")
                    
                    # Save to CSV
                    df.to_csv(save_path, index=False)
                    self.logger.info(f"Successfully saved {len(df)} records to {save_path}")
                else:
                    self.logger.error(f"No data collected for {position} {data_type} {year}")
                
            except Exception as e:
                self.logger.error(f"Error downloading {data_type} data for {position} {year}: {str(e)}")
                import traceback
                self.logger.debug(f"Traceback:\n{traceback.format_exc()}")
    
    def download_year_range(self, positions: List[str], start_year: int, end_year: int, save_dir: Path) -> None:
        """Download data for multiple positions over a range of years."""
        for year in range(start_year, end_year + 1):
            year_dir = save_dir / str(year)
            self.ensure_directory(year_dir)
            
            for position in positions:
                try:
                    self.download_position_data(position, year, year_dir)
                except Exception as e:
                    self.logger.error(f"Error downloading {position} data for {year}: {str(e)}")
                    import traceback
                    self.logger.debug(f"Traceback:\n{traceback.format_exc()}")
    
    def _download_page(self, url: str, position: str, data_type: str, year: int) -> Optional[List[Dict]]:
        """Download and parse a single page of data.
        
        Args:
            url: URL to download from
            position: Player position
            data_type: Type of data (projected or actual)
            year: Year of data
            
        Returns:
            List of dictionaries containing player data, or None if download fails
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Modify URL for actual stats to include games played
                if data_type == 'actual':
                    if '?' in url:
                        url = url + '&ShowG=Y'
                    else:
                        url = url + '?ShowG=Y'
                
                self.logger.debug(f"Requesting URL: {url} for {position} {data_type}")
                self.driver.get(url)
                time.sleep(2)  # Wait for page to load
                
                # Get page source and log length for debugging
                page_source = self.driver.page_source
                self.logger.debug(f"Page source length: {len(page_source)}")
                
                soup = BeautifulSoup(page_source, 'html5lib')
                
                # Look for the data table
                table = soup.find('table', {"width": "100%", "cellpadding": "2"})
                if not table:
                    self.logger.warning(f"No data table found at {url}")
                    return None
                
                # Log table structure for debugging
                self.logger.debug(f"Found table with structure:")
                headers = table.find_all('tr', class_='tableclmhdr')
                if headers:
                    for header in headers:
                        self.logger.debug(f"Header row: {header.get_text(strip=True)}")
                
                # Parse table into DataFrame
                table_html = StringIO(str(table))
                dfs = pd.read_html(table_html)
                
                if not dfs:
                    self.logger.warning("No tables found in HTML")
                    return None
                
                df = dfs[0]
                
                # Log raw DataFrame info
                self.logger.debug(f"Raw DataFrame info for {data_type}:")
                self.logger.debug(f"Columns before processing: {df.columns.tolist()}")
                self.logger.debug(f"First row before processing: {df.iloc[0].tolist()}")
                
                try:
                    # Process the table
                    df = self._process_table(df, position, data_type, year)
                    
                    # Log DataFrame info for debugging
                    self.logger.debug(f"DataFrame columns after processing: {df.columns.tolist()}")
                    self.logger.debug(f"DataFrame shape: {df.shape}")
                    self.logger.debug(f"First row of data:\n{df.iloc[0] if not df.empty else 'Empty DataFrame'}")
                    
                    # Convert to records
                    records = df.to_dict('records')
                    
                    # Validate records
                    valid_records = [
                        record for record in records 
                        if any(str(value).strip() for value in record.values())
                    ]
                    
                    if not valid_records:
                        self.logger.warning("No valid records found in table")
                        return None
                    
                    self.logger.debug(f"Downloaded {len(valid_records)} records from page {url}")
                    self.logger.debug(f"Sample record: {valid_records[0] if valid_records else None}")
                    return valid_records
                    
                except ValueError as e:
                    self.logger.warning(f"Error processing table: {str(e)}")
                    return None
                
            except Exception as e:
                self.logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(5)  # Wait before retry
                else:
                    self.logger.error(f"Failed to download {url} after {max_retries} attempts")
                    import traceback
                    self.logger.debug(f"Traceback:\n{traceback.format_exc()}")
                    return None