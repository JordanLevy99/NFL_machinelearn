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
        self.logger.debug(f"Sample data (first 2 rows):\n{df.head(2)}")
        self.logger.debug(f"Data types:\n{df.dtypes}")
        self.logger.debug(f"Null counts:\n{df.isnull().sum()}")
    
    def _process_table(self, df: pd.DataFrame, position: str, data_type: str) -> pd.DataFrame:
        """Process a raw table from FFToday into a clean DataFrame.
        
        Args:
            df: Raw DataFrame from HTML table
            position: Player position
            data_type: Type of data (projected or actual)
            
        Returns:
            Cleaned DataFrame with proper column names
        """
        self._debug_df_info(df, f"Raw table for {position} {data_type}")
        
        # Get the header rows
        header_row1 = df.iloc[0]
        header_row2 = df.iloc[1]
        
        # Drop the header rows and any empty rows
        df = df.iloc[2:].copy()
        df = df.dropna(how='all')
        
        # Combine header rows to create column names
        col_names = []
        for i in range(len(df.columns)):
            if pd.isna(header_row1[i]) and pd.isna(header_row2[i]):
                continue
            elif pd.isna(header_row1[i]):
                col_names.append(str(header_row2[i]).strip())
            elif pd.isna(header_row2[i]):
                col_names.append(str(header_row1[i]).strip())
            else:
                col_names.append(f"{header_row1[i]}_{header_row2[i]}".strip())
        
        # Map the combined headers to the expected column names
        header_mapping = {
            # Common columns
            'Chg': 'Change',
            'Player  Sort First: Last:': 'Name',
            'Tm': 'Team',
            'Team': 'Team',
            'Fantasy_FPts': 'FPts',
            'Fantasy_FPts/G': 'FPts/G',
            'G': 'GP',
            
            # QB columns - projected
            'Passing_Cmp': 'Comp',
            'Passing_Att': 'Pass Att',
            'Passing_Yds': 'Pass Yds',
            'Passing_TD': 'Pass TDs',
            'Passing_INT': 'Int',
            'Rushing_Att': 'Rush Att',
            'Rushing_Yds': 'Rush Yds',
            'Rushing_TD': 'Rush TDs',
            
            # QB columns - actual
            'Passing_Comp': 'Comp',
            'Passing_Yard': 'Pass Yds',
            'Rushing_Yard': 'Rush Yds',
            
            # RB columns - projected
            'Rushing_Att': 'Rush Att',
            'Rushing_Yds': 'Rush Yds',
            'Rushing_TD': 'Rush TDs',
            'Receiving_Rec': 'Rec',
            'Receiving_Yds': 'Rec Yds',
            'Receiving_TD': 'Rec TDs',
            
            # RB columns - actual
            'Rushing_Yard': 'Rush Yds',
            'Receiving_Yard': 'Rec Yds',
            
            # WR/TE columns - projected
            'Receiving_Rec': 'Rec',
            'Receiving_Yds': 'Rec Yds',
            'Receiving_TD': 'Rec TDs',
            
            # WR/TE columns - actual
            'Receiving_Yard': 'Rec Yds'
        }
        
        # Rename columns using the mapping
        df.columns = [header_mapping.get(col, col) for col in col_names]
        
        # Drop any remaining unnamed columns
        unnamed_cols = [col for col in df.columns if col.startswith('Unnamed:')]
        if unnamed_cols:
            df = df.drop(columns=unnamed_cols)
        
        # Validate required columns based on position
        expected_cols = CONFIG['STAT_COLUMNS'][position]
        missing_cols = [col for col in expected_cols if col not in df.columns]
        if missing_cols:
            self.logger.error(f"Missing columns in {data_type} data: {missing_cols}")
            self.logger.debug(f"Available columns: {df.columns.tolist()}")
            raise ValueError(f"Missing required columns for {position}: {missing_cols}")
        
        # Select and order columns
        df = df[expected_cols]
        
        # Convert numeric columns
        numeric_cols = [
            'Comp', 'Pass Att', 'Pass Yds', 'Pass TDs', 'Int',
            'Rush Att', 'Rush Yds', 'Rush TDs',
            'Rec', 'Rec Yds', 'Rec TDs',
            'GP', 'FPts'
        ]
        
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Validate data quality
        if df.isnull().all().any():
            null_cols = df.columns[df.isnull().all()].tolist()
            self.logger.error(f"Found columns with all null values: {null_cols}")
            raise ValueError(f"Found columns with all null values: {null_cols}")
        
        if len(df) == 0:
            raise ValueError(f"No valid data found for {position} {data_type}")
        
        self._debug_df_info(df, f"Processed table for {position} {data_type}")
        return df
    
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
                self.logger.info(f"Downloading {data_type} data for {position} {year}")
                
                all_data = []
                for page in range(position_info['pages']):
                    # Construct URL based on data type
                    if data_type == 'projected':
                        url = f"{self.base_url}/rankings/playerproj.php?&PosID={position_info['id']}&Season={year}&LeagueID={CONFIG['LEAGUE_ID']}&cur_page={page}"
                    else:
                        url = f"{self.base_url}/stats/playerstats.php?Season={year}&GameWeek=&PosID={position_info['id']}&LeagueID={CONFIG['LEAGUE_ID']}&cur_page={page}"
                    
                    self.logger.debug(f"Downloading from URL: {url}")
                    
                    # Get page data
                    page_data = self._download_page(url, position, data_type)
                    if page_data is not None:
                        self.logger.debug(f"Downloaded {len(page_data)} records from page {page}")
                        all_data.extend(page_data)
                    else:
                        self.logger.warning(f"No data found on page {page}")
                    
                    time.sleep(3)  # Be nice to the server
                
                # Save data
                if all_data:
                    save_path = save_dir / f"{position}_{data_type}.csv"
                    
                    # Convert to DataFrame
                    df = pd.DataFrame(all_data)
                    self._debug_df_info(df, f"Final data for {position} {data_type}")
                    
                    # Save to CSV
                    df.to_csv(save_path, index=False)
                    self.logger.info(f"Saved {len(df)} records to {save_path}")
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
    
    def _download_page(self, url: str, position: str, data_type: str) -> Optional[List[Dict]]:
        """Download and parse a single page of data."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
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
                    self.logger.debug("Page source preview:")
                    self.logger.debug(page_source[:500])
                    return None
                
                # Parse table into DataFrame
                table_html = StringIO(str(table))
                dfs = pd.read_html(table_html)
                
                if not dfs:
                    self.logger.warning("No tables found in HTML")
                    return None
                
                df = dfs[0]
                
                try:
                    # Process the table
                    df = self._process_table(df, position, data_type)
                    
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