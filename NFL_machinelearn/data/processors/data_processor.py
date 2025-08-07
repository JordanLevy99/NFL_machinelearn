import numpy as np
import pandas as pd
from pathlib import Path
import logging
from typing import Dict, List, Optional
from NFL_machinelearn.config.config import CONFIG

class DataProcessor:
    """Processes raw NFL player data for model training.
    
    This class handles:
    - Loading and formatting raw CSV data
    - Merging projected and actual stats
    - Adjusting stats for games played
    - Standardizing features
    - Removing outliers
    """
    
    POSITIONS = CONFIG['STAT_COLUMNS']
    
    def __init__(self, data_dir: Path):
        """Initialize the data processor.
        
        Args:
            data_dir: Base directory containing raw data
        """
        self.data_dir = Path(data_dir)
        self.logger = logging.getLogger(__name__)
    
    def _debug_df_info(self, df: pd.DataFrame, stage: str) -> None:
        """Print debug information about a DataFrame.
        
        Args:
            df: DataFrame to inspect
            stage: Description of the current processing stage
        """
        self.logger.debug(f"\n{'='*20} {stage} {'='*20}")
        self.logger.debug(f"Shape: {df.shape}")
        self.logger.debug(f"Columns: {df.columns.tolist()}")
        self.logger.debug(f"Sample data (first 2 rows):\n{df.head(2)}")
        if 'GP' in df.columns:
            self.logger.debug(f"GP column stats:\n{df['GP'].describe()}")
        elif 'Bye' in df.columns:
            self.logger.debug(f"Bye column stats:\n{df['Bye'].describe()}")
    
    def load_raw_data(self, position: str, data_type: str, year: int) -> pd.DataFrame:
        """Load raw data from CSV file."""
        file_path = self.data_dir / str(year) / f"{position}_{data_type}.csv"
        if not file_path.exists():
            raise FileNotFoundError(f"Data file not found: {file_path}")
        
        df = pd.read_csv(file_path)
        
        # Clean up column names
        df.columns = [col.strip() for col in df.columns]
        
        # Clean up player names (remove rank numbers)
        if 'Name' in df.columns:
            df['Name'] = df['Name'].str.replace(r'^\d+\.\s*', '', regex=True)
        
        # Check for 'Bye' column
        if 'Bye' in df.columns:
            self.logger.debug(f"Found 'Bye' column in {position} {year} data")
            df = df.drop(columns=['Bye'])
        else:
            self.logger.debug(f"No 'Bye' column found in {position} {year} data")
        
        # Get required columns for this position
        columns_to_keep = CONFIG['STAT_COLUMNS'][position]
        
        # Check for missing columns
        missing_cols = [col for col in columns_to_keep if col not in df.columns]
        if missing_cols:
            self.logger.warning(f"Missing columns for {position} {year}: {missing_cols}")
            self.logger.debug(f"Available columns: {df.columns.tolist()}")
            
            # Handle missing GP column
            if 'GP' in missing_cols and 'G' in df.columns:
                df = df.rename(columns={'G': 'GP'})
                missing_cols.remove('GP')
            elif 'GP' in missing_cols:
                # If GP is missing, and we can't find it, add it with default value
                df['GP'] = 17 if year >= 2021 else 16
                missing_cols.remove('GP')
            
            # If there are still missing columns, raise error
            if missing_cols:
                raise ValueError(f"Missing required columns: {missing_cols}")
        
        # Select and order columns
        df = df[columns_to_keep]
        
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
        
        return df
    
    def merge_projected_actual(self, position: str, start_year: int, end_year: int) -> pd.DataFrame:
        """Merge projected and actual data for a given position over a range of years.
        
        Args:
            position: Player position (QB, RB, WR, TE)
            start_year: Starting year for data range
            end_year: Ending year for data range (inclusive)
            
        Returns:
            DataFrame with merged projected and actual stats across years
        """
        try:
            all_merged = []
            
            for year in range(start_year, end_year + 1):
                # Load projected and actual data for this year
                projected = self.load_raw_data(position, 'projected', year)
                actual = self.load_raw_data(position, 'actual', year)

                logging.debug(f"Columns of projected data:\n{projected.columns.tolist()}")
                logging.debug(f"Columns of actual data:\n{actual.columns.tolist()}")
                
                # Add GP column to projected data if it doesn't exist
                if 'GP' not in projected.columns:
                    games_in_season = 17 if year >= 2021 else 16
                    projected['GP'] = games_in_season
                
                # Merge on player name and team
                merged = pd.merge(
                    projected,
                    actual, 
                    on=['Name', 'Team'],
                    how='inner',
                    suffixes=('_projected', '_actual')
                )
                
                # Add year column
                merged['Yr'] = year
                
                # Ensure GP column exists in merged DataFrame
                if 'GP_actual' in merged.columns:
                    merged['GP'] = merged['GP_actual']
                elif 'GP_projected' in merged.columns:
                    merged['GP'] = merged['GP_projected']
                
                # Rename fantasy points columns
                if 'FPts_projected' in merged.columns:
                    merged['Proj FPts'] = merged['FPts_projected']
                if 'FPts_actual' in merged.columns:
                    merged['Act FPts'] = merged['FPts_actual']
                
                # debug statements on merged data
                self.logger.debug(f"Columns of merged data:\n{merged.columns.tolist()}")
                
                # Adjust stats based on games played only if we have actual GP data
                if 'GP_actual' in merged.columns:
                    games_in_season = 17 if year >= 2021 else 16
                    for col in CONFIG['STAT_COLUMNS'][position]:
                        if col not in ['Name', 'Team', 'GP', 'FPts']:
                            # Adjust projected stats
                            proj_col = f"{col}_projected"
                            if proj_col in merged.columns:
                                merged[proj_col] = merged[proj_col] * (merged['GP_actual'] / games_in_season)
                            
                            # Adjust actual stats  
                            actual_col = f"{col}_actual"
                            if actual_col in merged.columns:
                                merged[actual_col] = merged[actual_col] * (games_in_season / merged['GP_actual'])
                
                all_merged.append(merged)
            
            # Combine all years
            final_merged = pd.concat(all_merged, ignore_index=True)
            return final_merged
            
        except Exception as e:
            self.logger.error(f"Error merging data for {position} {start_year}-{end_year}: {str(e)}")
            import traceback
            self.logger.debug(f"Traceback:\n{traceback.format_exc()}")
            raise
    
    def adjust_for_games_played(self, df: pd.DataFrame, min_games: int = 13) -> pd.DataFrame:
        """Adjust stats based on games played and remove outliers.
        
        Args:
            df: DataFrame containing player stats
            min_games: Minimum number of games played to include
            
        Returns:
            DataFrame with adjusted stats and outliers removed
        """
        # Filter for minimum games played
        df = df[df['GP'] > min_games].copy()
        
        # Scale stats to 16-game season
        df['Act FPts'] = df.apply(
            lambda row: (16 / row['GP'] * row['Act FPts']), 
            axis=1
        )
        
        # Remove outliers based on absolute error between projected and actual points
        absolute_error = abs(df['Act FPts'] - df['Proj FPts'])
        Q1 = absolute_error.quantile(0.25)
        Q3 = absolute_error.quantile(0.75)
        IQR = Q3 - Q1
        outlier_limit = 1.5 * IQR
        
        return df[absolute_error <= outlier_limit]
    
    def standardize_features(self, df: pd.DataFrame, exclude_cols: List[str] = None) -> pd.DataFrame:
        """Standardize features by year.
        
        Args:
            df: DataFrame to standardize
            exclude_cols: Columns to exclude from standardization
            
        Returns:
            DataFrame with standardized features
        """
        if exclude_cols is None:
            exclude_cols = ['Name', 'Team']
            
        # Group by year and standardize
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        numeric_cols = [col for col in numeric_cols if col not in exclude_cols]
        
        df_std = df.copy()
        df_std[numeric_cols] = df.groupby('Yr')[numeric_cols].transform(lambda x: (x - x.mean()) / x.std())
        
        return df_std.fillna(0)
    
    def process_training_data(self, position: str, start_year: int, end_year: int) -> pd.DataFrame:
        """Process raw data into training data.
        
        This method combines all processing steps:
        1. Merge projected and actual data
        2. Adjust for games played
        3. Standardize features
        
        Args:
            position: Player position
            start_year: Start year for training data
            end_year: End year for training data
            
        Returns:
            Processed DataFrame ready for training
        """
        self.logger.info(f"Processing {position} data from {start_year} to {end_year}")
        
        # Merge projected and actual data
        df = self.merge_projected_actual(position, start_year, end_year)
        
        # Adjust for games played and remove outliers
        df = self.adjust_for_games_played(df)
        
        # Standardize features
        df = self.standardize_features(df)
        
        self.logger.info(f"Processed {len(df)} records for {position}")
        return df 