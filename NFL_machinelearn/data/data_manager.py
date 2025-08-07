from typing import Dict, List, Optional, Tuple
import pandas as pd
from pathlib import Path
import logging
from datetime import datetime
import os

class DataManager:
    """Manages NFL data operations including storage, retrieval, and validation.
    
    This class handles:
    - Checking for existing data
    - Managing data paths
    - Loading and combining data sets
    - Data validation
    """
    
    def __init__(self, base_data_dir: Path):
        """Initialize the data manager.
        
        Args:
            base_data_dir: Base directory for all data storage
        """
        self.base_data_dir = Path(base_data_dir)
        self.logger = logging.getLogger(__name__)
        
        # Create standard directory structure
        self.raw_data_dir = self.base_data_dir / 'raw'
        self.processed_data_dir = self.base_data_dir / 'processed'
        self.models_dir = self.base_data_dir / 'models'
        
        self._create_directories()
        
    def _create_directories(self) -> None:
        """Create necessary directory structure if it doesn't exist."""
        for directory in [self.raw_data_dir, self.processed_data_dir, self.models_dir]:
            directory.mkdir(parents=True, exist_ok=True)
            
    def get_data_path(self, year: int, position: str, data_type: str) -> Path:
        """Get the path for a specific data file.
        
        Args:
            year: The year of the data
            position: Player position (QB, RB, WR, TE)
            data_type: Type of data (projected or actual)
            
        Returns:
            Path to the data file
        """
        return self.raw_data_dir / str(year) / f"{position}_{data_type}.csv"
        
    def check_data_exists(self, start_year: int, end_year: int, position: str) -> Dict[int, List[str]]:
        """Check if data exists for a given position and year range.
        
        Args:
            start_year: Start year for data range
            end_year: End year for data range (inclusive)
            position: Player position (QB, RB, WR, TE)
            
        Returns:
            Dictionary mapping years to list of missing data types ('projected' or 'actual')
        """
        missing_files = {}
        
        for year in range(start_year, end_year + 1):
            year_missing = []
            
            # Check projected data
            if not (self.raw_data_dir / str(year) / f"{position}_projected.csv").exists():
                year_missing.append('projected')
                
            # Check actual data
            if not (self.raw_data_dir / str(year) / f"{position}_actual.csv").exists():
                year_missing.append('actual')
                
            if year_missing:
                missing_files[year] = year_missing
                
        return missing_files
    
    def load_position_data(self, year: int, position: str, data_type: str) -> pd.DataFrame:
        """Load data for a specific position and year.
        
        Args:
            year: The year to load data for
            position: Player position
            data_type: Type of data (projected or actual)
            
        Returns:
            DataFrame containing the requested data
        """
        data_path = self.get_data_path(year, position, data_type)
        if not data_path.exists():
            raise FileNotFoundError(f"No {data_type} data found for {position} {year}")
            
        try:
            return pd.read_csv(data_path)
        except Exception as e:
            self.logger.error(f"Error loading {data_type} data for {position} {year}: {str(e)}")
            raise
    
    def load_training_data(self, start_year: int, end_year: int, position: str) -> pd.DataFrame:
        """Load and combine training data for a range of years.
        
        Args:
            start_year: Start year (inclusive)
            end_year: End year (inclusive)
            position: Player position
            
        Returns:
            Combined DataFrame of all available data
        """
        dfs = []
        for year in range(start_year, end_year + 1):
            try:
                projected_df = self.load_position_data(year, position, "projected")
                actual_df = self.load_position_data(year, position, "actual")
                
                # Merge projected and actual data
                year_df = projected_df.merge(
                    actual_df,
                    how='inner',
                    on=['Name', 'Team']
                )
                year_df['Year'] = year
                dfs.append(year_df)
                
            except Exception as e:
                self.logger.error(f"Error loading data for {year} {position}: {str(e)}")
                continue
                
        if not dfs:
            raise ValueError(f"No valid data found for {position} between {start_year}-{end_year}")
            
        return pd.concat(dfs, ignore_index=True)
        
    def save_processed_data(self, data: pd.DataFrame, position: str) -> Path:
        """Save processed training data with timestamp.
        
        Args:
            data: Processed DataFrame to save
            position: Player position
            
        Returns:
            Path where data was saved
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{position}_processed_{timestamp}.csv"
        save_path = self.processed_data_dir / filename
        
        data.to_csv(save_path, index=False)
        self.logger.info(f"Saved processed data to {save_path}")
        return save_path
        
    def get_latest_model_path(self, position: str) -> Optional[Path]:
        """Get the path to the latest saved model for a position.
        
        Args:
            position: Player position
            
        Returns:
            Path to latest model or None if no model exists
        """
        model_files = list(self.models_dir.glob(f"{position}_model_*.joblib"))
        if not model_files:
            return None
            
        # Return most recently modified model
        return max(model_files, key=os.path.getmtime)
        
    def save_model(self, position: str, model_path: Path) -> None:
        """Save a model file to the models directory.
        
        Args:
            position: Player position
            model_path: Path to the model file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_path = self.models_dir / f"{position}_model_{timestamp}.joblib"
        
        # Copy model file to models directory
        import shutil
        shutil.copy2(model_path, new_path)
        self.logger.info(f"Saved model to {new_path}") 
        
    def has_required_data(self, start_year: int, end_year: int) -> bool:
        """Check if all required data exists for the given year range.
        
        Args:
            start_year: Start year (inclusive)
            end_year: End year (inclusive)
            
        Returns:
            bool: True if all required data exists, False otherwise
        """
        positions = ['QB', 'RB', 'WR', 'TE']
        data_types = ['projected', 'actual']
        
        for year in range(start_year, end_year + 1):
            for position in positions:
                for data_type in data_types:
                    if not self.check_data_exists(year, position, data_type):
                        self.logger.debug(f"Missing data for {year} {position} {data_type}")
                        return False
        
        return True