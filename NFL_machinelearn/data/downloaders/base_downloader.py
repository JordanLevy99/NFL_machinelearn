from abc import ABC, abstractmethod
from pathlib import Path
import logging
from typing import List, Dict, Any

class BaseDownloader(ABC):
    """Base class for all data downloaders.
    
    This abstract class defines the interface that all downloaders must implement.
    It provides basic functionality for downloading and saving NFL player data.
    """
    
    def __init__(self):
        """Initialize the base downloader."""
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def download_position_data(self, position: str, year: int, save_dir: Path) -> None:
        """Download data for a specific position and year.
        
        Args:
            position: Player position (QB, RB, WR, TE)
            year: Year to download data for
            save_dir: Directory to save downloaded data
        """
        pass
    
    @abstractmethod
    def download_year_range(self, positions: List[str], start_year: int, end_year: int, save_dir: Path) -> None:
        """Download data for multiple positions over a range of years.
        
        Args:
            positions: List of positions to download
            start_year: Start year for data range
            end_year: End year for data range
            save_dir: Directory to save downloaded data
        """
        pass
    
    def ensure_directory(self, directory: Path) -> None:
        """Ensure a directory exists, creating it if necessary.
        
        Args:
            directory: Directory path to ensure exists
        """
        directory.mkdir(parents=True, exist_ok=True)
