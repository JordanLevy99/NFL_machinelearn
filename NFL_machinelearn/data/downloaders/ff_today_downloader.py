from pathlib import Path
import time
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
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
        try:
            self.driver.set_page_load_timeout(15)
            self.driver.set_script_timeout(15)
        except Exception:
            pass
        self.base_url = CONFIG['BASE_URL']
        self.positions = CONFIG['POSITIONS']
        self.logger = logging.getLogger(__name__)

    def _debug_df_info(self, df: pd.DataFrame, stage: str) -> None:
        """Print debug information about a DataFrame."""
        self.logger.debug(f"\n{'=' * 20} {stage} {'=' * 20}")
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
                # Fallback for projected weekly tables that include extra columns / different header casings
                if data_type == 'projected':
                    # Try to use first row as headers and select expected columns
                    try:
                        headers_row = df.iloc[0]
                        df2 = df.iloc[1:].copy()
                        df2.columns = [str(h).strip() for h in headers_row]
                        # Normalize common FFToday header variants
                        rename_map = {
                            'Player': 'Name',
                            'TEAM': 'Team', 'Team': 'Team',
                            'REC': 'Rec', 'Recs': 'Rec', 'Rec.': 'Rec',
                            'YDS': 'Rec Yds', 'Yds': 'Rec Yds', 'REC YDS': 'Rec Yds', 'Rec Yds': 'Rec Yds',
                            'TD': 'Rec TDs', 'TDS': 'Rec TDs', 'Rec TD': 'Rec TDs', 'Rec TDs': 'Rec TDs',
                            'FPTS': 'FPts', 'FPTs': 'FPts', 'Fpts': 'FPts', 'FPts': 'FPts',
                            'BYE': 'Bye', 'Bye Week': 'Bye',
                        }
                        df2 = df2.rename(columns={c: rename_map.get(c, c) for c in df2.columns})
                        expected = CONFIG['DOWNLOAD_COLUMNS']['projected'][position]
                        available = [c for c in expected if c in df2.columns]
                        if len(available) >= 5:  # require most columns
                            df = df2[available].copy()
                            # If Bye missing, add
                            if 'Bye' in expected and 'Bye' not in df.columns:
                                df['Bye'] = None
                            # Reorder to expected order subset
                            order = [c for c in expected if c in df.columns]
                            df = df[order]
                        else:
                            # TE weekly often shows duplicate 'Yard' and 'TD' columns (rushing and receiving)
                            cols = list(df2.columns)
                            def find_first(name: str):
                                for c in cols:
                                    if c.lower() == name.lower():
                                        return c
                                return None
                            def find_fuzzy(sub: str):
                                for c in cols:
                                    if sub.lower() in c.lower():
                                        return c
                                return None
                            name_col = find_first('Name') or find_first('Player')
                            team_col = find_first('Team')
                            rec_col = find_first('Rec')
                            # Disambiguate Yard/TD: take the LAST occurrence on the row as receiving
                            yard_positions = [i for i,c in enumerate(cols) if c.lower() in ('yard','yds','yards')]
                            td_positions = [i for i,c in enumerate(cols) if c.lower() == 'td' or c.lower() == 'tds']
                            rec_yds_col = None
                            rec_tds_col = None
                            if 'Rec Yds' in cols:
                                rec_yds_col = 'Rec Yds'
                            elif yard_positions:
                                rec_yds_col = cols[yard_positions[-1]]
                            if 'Rec TDs' in cols:
                                rec_tds_col = 'Rec TDs'
                            elif td_positions:
                                rec_tds_col = cols[td_positions[-1]]
                            fpts_col = find_first('FPts') or find_fuzzy('FP')

                            picked = [name_col, team_col, rec_col, rec_yds_col, rec_tds_col, fpts_col]
                            if all(picked):
                                df = df2[[name_col, team_col, rec_col, rec_yds_col, rec_tds_col, fpts_col]].copy()
                                df.columns = ['Name', 'Team', 'Rec', 'Rec Yds', 'Rec TDs', 'FPts']
                                if 'Bye' in expected and 'Bye' not in df.columns:
                                    df['Bye'] = None
                            else:
                                raise ValueError(f"Insufficient matching headers for weekly {position}: {df2.columns.tolist()}")
                    except Exception as ie:
                        raise ValueError(f"Column mismatch for {position} {data_type}: {len(df.columns)} columns found") from ie
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

    def download_position_data(self, position: str, year: int, save_dir: Path) -> Dict[str, pd.DataFrame]:
        """Download data for a specific position and year.
        
        Returns:
            Dict with keys 'actual' and 'projected', containing respective DataFrames
        """
        if position not in self.positions:
            raise ValueError(f"Invalid position: {position}")

        position_info = self.positions[position]
        self.ensure_directory(save_dir)
        
        results = {}
        
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
                    self.logger.debug(
                        f"First record in final DataFrame: {df.iloc[0].to_dict() if len(df) > 0 else None}")

                    # Save to CSV
                    df.to_csv(save_path, index=False)
                    self.logger.info(f"Successfully saved {len(df)} records to {save_path}")
                    results[data_type] = df
                else:
                    self.logger.error(f"No data collected for {position} {data_type} {year}")
                    results[data_type] = pd.DataFrame()

            except Exception as e:
                self.logger.error(f"Error downloading {data_type} data for {position} {year}: {str(e)}")
                import traceback
                self.logger.debug(f"Traceback:\n{traceback.format_exc()}")
                results[data_type] = pd.DataFrame()

        return results

    def download_weekly_position_projections(self, position: str, year: int, week: int,
                                             pages_limit: Optional[int] = None,
                                             delay_seconds: float = 1.0) -> pd.DataFrame:
        """Download WEEKLY projected data for a specific position and week.

        Args:
            position: Player position (QB/RB/WR/TE)
            year: Season year
            week: Game week (1-18)

        Returns:
            DataFrame of weekly projections with standardized columns
        """
        if position not in self.positions:
            raise ValueError(f"Invalid position: {position}")

        position_info = self.positions[position]
        all_data: List[Dict] = []

        total_pages = pages_limit if pages_limit is not None else position_info['pages']
        for page in range(total_pages):
            self.logger.info(f"[FFToday][weekly] {position} {year} wk{week}: scraping page {page+1}/{position_info['pages']}")
            url = (
                f"{self.base_url}/rankings/playerwkproj.php?Season={year}&GameWeek={week}"
                f"&PosID={position_info['id']}&LeagueID={CONFIG['LEAGUE_ID']}&cur_page={page}"
            )
            if page == 0:
                # Log only once per position to avoid spam
                self.logger.info(f"[FFToday][weekly][URL] {url}")

            page_data = self._download_week_page(url, position, year)
            if page_data:
                all_data.extend(page_data)
            time.sleep(max(0.0, delay_seconds))

        if not all_data:
            self.logger.error(f"No weekly projected data collected for {position} {year} wk{week}")
            return pd.DataFrame()

        df = pd.DataFrame(all_data)
        # Ensure final column set aligns to projected config
        expected_cols = CONFIG['DOWNLOAD_COLUMNS']['projected'][position]
        missing = [c for c in expected_cols if c not in df.columns]
        if missing:
            self.logger.warning(f"Weekly {position} missing expected columns: {missing}")
        return df[ [c for c in expected_cols if c in df.columns] ]

    def download_weekly_projections(self, positions: List[str], year: int, week: int, save_dir: Path,
                                    pages_limit: Optional[int] = None,
                                    delay_seconds: float = 1.0) -> Dict[str, pd.DataFrame]:
        """Download WEEKLY projected data for multiple positions for a given week and save as CSVs.

        Returns a dict mapping position -> DataFrame.
        """
        results: Dict[str, pd.DataFrame] = {}
        self.ensure_directory(save_dir)
        for position in positions:
            try:
                df = self.download_weekly_position_projections(position, year, week,
                                                               pages_limit=pages_limit,
                                                               delay_seconds=delay_seconds)
                results[position] = df
                if not df.empty:
                    out = save_dir / f"{position}_projected_week{week}.csv"
                    df.to_csv(out, index=False)
                    self.logger.info(f"Saved {len(df)} weekly {position} projections to {out}")
            except Exception as e:
                self.logger.error(f"Error downloading weekly {position} {year} wk{week}: {e}")
                results[position] = pd.DataFrame()
        return results

    def _download_week_page(self, url: str, position: str, year: int) -> Optional[List[Dict]]:
        """Download and parse a weekly projections page to a list of dicts."""
        try:
            if position == 'TE' and 'cur_page=0' in url:
                self.logger.info(f"[FFToday][weekly] GET {url}")
            try:
                self.driver.get(url)
            except TimeoutException:
                self.logger.warning(f"[FFToday][weekly] GET timeout; skipping: {url}")
                return None
            time.sleep(2)
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html5lib')

            # FFToday weekly pages use a full-width data table similar to season pages
            table = soup.find('table', {"width": "100%", "cellpadding": "2"})
            if not table:
                # Fallback: first table that contains 'FPts' header
                for t in soup.find_all('table'):
                    if 'FPts' in t.get_text():
                        table = t
                        break
            if not table:
                self.logger.warning(f"No weekly table found at {url}")
                return None

            from io import StringIO
            # Use header row so pandas assigns proper column names for weekly pages
            dfs = pd.read_html(StringIO(str(table)), header=1)
            if not dfs:
                return None
            df = dfs[0]

            # TE weekly pages include Rushing and Receiving sub-columns. Select Receiving set.
            if position == 'TE':
                import re
                cols = [re.sub(r"\s+", " ", str(c)).strip() for c in df.columns]
                df.columns = cols
                # Drop known non-data columns
                for drop in ['Chg', 'Sort First:', 'Last:', 'Opp', 'Att', 'Yard', 'TD']:
                    if drop in df.columns:
                        # For Yard/TD we only want to keep the Receiving ones; they appear twice.
                        # We'll handle selection below, so just skip dropping here.
                        pass
                # Identify columns
                name_col = None
                for cand in ['Player', 'Name', 'Player Sort First: Last:']:
                    if cand in df.columns:
                        name_col = cand
                        break
                team_col = 'Team' if 'Team' in df.columns else None
                rec_col = 'Rec' if 'Rec' in df.columns else None
                # Yard/TD: pick the last occurrence which corresponds to Receiving
                if 'Yard.1' in df.columns:
                    rec_yds_col = 'Yard.1'
                else:
                    yard_cols = [c for c in df.columns if c.lower() in ('yard', 'yds', 'yards')]
                    rec_yds_col = yard_cols[-1] if yard_cols else None
                if 'TD.1' in df.columns:
                    rec_tds_col = 'TD.1'
                else:
                    td_cols = [c for c in df.columns if c.upper().startswith('TD')]
                    rec_tds_col = td_cols[-1] if td_cols else None
                fpts_col = 'FPts' if 'FPts' in df.columns else (next((c for c in df.columns if 'FP' in c), None))
                picked = [name_col, team_col, rec_col, rec_yds_col, rec_tds_col, fpts_col]
                if all(picked):
                    df = df[[name_col, team_col, rec_col, rec_yds_col, rec_tds_col, fpts_col]].copy()
                    df.columns = ['Name', 'Team', 'Rec', 'Rec Yds', 'Rec TDs', 'FPts']
                    if 'Bye' in CONFIG['DOWNLOAD_COLUMNS']['projected']['TE'] and 'Bye' not in df.columns:
                        df['Bye'] = None
                    if 'GP' not in df.columns:
                        df['GP'] = 1
                else:
                    self.logger.warning(f"TE weekly header selection failed. Columns: {df.columns.tolist()}")
                    return None
            else:
                # Reuse existing processor with 'projected' mapping
                df = self._process_table(df, position, 'projected', year)
            if df.empty:
                return None
            return df.to_dict('records')
        except Exception as e:
            self.logger.warning(f"Failed to parse weekly page: {e}")
            return None

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
            # Removed verbose structure dump now that parsing works reliably
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
