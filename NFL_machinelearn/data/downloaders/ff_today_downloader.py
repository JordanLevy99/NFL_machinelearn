from pathlib import Path
import time
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from typing import Dict, List, Optional
from io import StringIO

from .base_downloader import BaseDownloader
from NFL_machinelearn.config.config import CONFIG

class FFTodayDownloader(BaseDownloader):
    """Downloads NFL player data from FFToday.com."""
    
    def __init__(self, driver: webdriver.Chrome):
        """Initialize the FFToday downloader.
        
        Args:
            driver: Configured Chrome WebDriver instance
        """
        super().__init__()
        self.driver = driver
        self.base_url = CONFIG['BASE_URL']
        self.positions = CONFIG['POSITIONS']
    
    def download_position_data(self, position: str, year: int, save_dir: Path) -> None:
        """Download data for a specific position and year.
        
        Args:
            position: Player position (QB, RB, WR, TE)
            year: Year to download data for
            save_dir: Directory to save downloaded data
        """
        if position not in self.positions:
            raise ValueError(f"Invalid position: {position}")
            
        position_info = self.positions[position]
        
        # Ensure save directory exists
        self.ensure_directory(save_dir)
        
        # Download both projected and actual data
        for data_type in ['projected', 'actual']:
            self.logger.info(f"Downloading {data_type} data for {position} {year}")
            
            all_data = []
            for page in range(position_info['pages']):
                # Construct URL based on data type
                if data_type == 'projected':
                    url = f"{self.base_url}/rankings/playerproj.php?&PosID={position_info['id']}&Season={year}&LeagueID={CONFIG['LEAGUE_ID']}&cur_page={page}"
                else:
                    url = f"{self.base_url}/stats/playerstats.php?Season={year}&GameWeek=&PosID={position_info['id']}&LeagueID={CONFIG['LEAGUE_ID']}&cur_page={page}"
                
                # Get page data
                page_data = self._download_page(url, position, data_type)
                if page_data is not None:
                    all_data.extend(page_data)
                
                time.sleep(3)  # Be nice to the server
            
            # Save data
            if all_data:
                save_path = save_dir / f"{position}_{data_type}.csv"
                df = pd.DataFrame(all_data, columns=CONFIG['STAT_COLUMNS'][position])
                df.to_csv(save_path, index=False)
                self.logger.info(f"Saved {len(df)} records to {save_path}")
    
    def download_year_range(self, positions: List[str], start_year: int, end_year: int, save_dir: Path) -> None:
        """Download data for multiple positions over a range of years.
        
        Args:
            positions: List of positions to download
            start_year: Start year for data range
            end_year: End year for data range
            save_dir: Directory to save downloaded data
        """
        for year in range(start_year, end_year + 1):
            year_dir = save_dir / str(year)
            self.ensure_directory(year_dir)
            
            for position in positions:
                try:
                    self.download_position_data(position, year, year_dir)
                except Exception as e:
                    self.logger.error(f"Error downloading {position} data for {year}: {str(e)}")
    
    def _download_page(self, url: str, position: str, data_type: str) -> Optional[List[Dict]]:
        """Download and parse a single page of data.
        
        Args:
            url: URL to download from
            position: Player position
            data_type: Type of data (projected or actual)
            
        Returns:
            List of player data dictionaries or None if download fails
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.driver.get(url)
                soup = BeautifulSoup(self.driver.page_source, 'html5lib')
                table = soup.find('table', {"width": "100%", "cellpadding": "2"})
                if not table:
                    self.logger.warning(f"No data table found at {url}")
                    return None
                
                # Parse table into DataFrame using StringIO to avoid FutureWarning
                table_html = StringIO(str(table))
                df = pd.read_html(table_html)[0]
                return df.to_dict('records')
                
            except Exception as e:
                self.logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(5)  # Wait before retry
                else:
                    self.logger.error(f"Failed to download {url} after {max_retries} attempts")
                    return None