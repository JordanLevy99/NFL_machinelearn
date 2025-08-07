from typing import List, Optional, Dict, Union, Tuple
import numpy as np
import pandas as pd
from dataclasses import dataclass
from sklearn.base import BaseEstimator
from sklearn.preprocessing import StandardScaler
from sklearn.neural_network import MLPRegressor
from sklearn.metrics import mean_squared_error, r2_score
import logging
from pathlib import Path

@dataclass
class ModelConfig:
    """Configuration for the ML model."""
    hidden_layers: List[int]
    activation: str
    alpha: float
    max_iter: int
    validation_fraction: float = 0.2
    early_stopping: bool = True
    
@dataclass
class ModelMetrics:
    """Store model performance metrics."""
    mse: float
    rmse: float
    r2: float
    validation_score: float

class NFLPredictor:
    """Neural Network based predictor for NFL player statistics.
    
    This class handles the entire ML pipeline including:
    - Data preprocessing
    - Feature scaling
    - Model training
    - Prediction
    - Performance evaluation
    """
    
    def __init__(self, config: ModelConfig):
        """Initialize the predictor with model configuration.
        
        Args:
            config: ModelConfig instance containing model parameters
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.model: Optional[BaseEstimator] = None
        self.scaler: Optional[StandardScaler] = None
        self.feature_columns: List[str] = []
        
    def _initialize_model(self) -> None:
        """Initialize the MLPRegressor with configured parameters."""
        self.model = MLPRegressor(
            hidden_layer_sizes=self.config.hidden_layers,
            activation=self.config.activation,
            alpha=self.config.alpha,
            max_iter=self.config.max_iter,
            validation_fraction=self.config.validation_fraction,
            early_stopping=self.config.early_stopping
        )
        
    def preprocess_data(self, data: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
        """Clean and preprocess the input data.
        
        Args:
            data: Raw input DataFrame
            
        Returns:
            Tuple of (preprocessed DataFrame, list of feature columns)
        """
        try:
            # Remove rows with missing values
            cleaned_data = data.dropna()
            
            # Convert categorical variables if present
            for col in cleaned_data.select_dtypes(['object']).columns:
                if col != 'Name':  # Keep player names as is
                    cleaned_data[col] = pd.Categorical(cleaned_data[col]).codes
            
            # Identify feature columns (only projected stats, excluding target and metadata)
            exclude_patterns = ['Name', 'Team', 'Act FPts', 'actual', 'Proj FPts']
            self.feature_columns = [col for col in cleaned_data.columns 
                                  if not any(pattern in col for pattern in exclude_patterns)
                                  and ('projected' in col or not any(suffix in col for suffix in ['_projected', '_actual']))]
            
            self.logger.info(f"Data preprocessed successfully. Features: {self.feature_columns}")
            return cleaned_data, self.feature_columns
            
        except Exception as e:
            self.logger.error(f"Error in data preprocessing: {str(e)}")
            raise
            
    def scale_features(self, X: pd.DataFrame, fit: bool = True) -> np.ndarray:
        """Scale features using StandardScaler.
        
        Args:
            X: Feature DataFrame
            fit: Whether to fit the scaler or use existing transformation
            
        Returns:
            Scaled features as numpy array
        """
        if fit:
            self.scaler = StandardScaler()
            return self.scaler.fit_transform(X)
        return self.scaler.transform(X)
        
    def train(self, X: pd.DataFrame, y: pd.Series) -> ModelMetrics:
        """Train the model and return performance metrics.
        
        Args:
            X: Feature DataFrame
            y: Target series
            
        Returns:
            ModelMetrics containing performance measures
        """
        try:
            if not self.model:
                self._initialize_model()
                
            # Scale features
            X_scaled = self.scale_features(X, fit=True)
            
            # Train model
            self.model.fit(X_scaled, y)
            
            # Calculate metrics
            y_pred = self.model.predict(X_scaled)
            mse = mean_squared_error(y, y_pred)
            metrics = ModelMetrics(
                mse=mse,
                rmse=np.sqrt(mse),
                r2=r2_score(y, y_pred),
                validation_score=self.model.validation_scores_[-1] if self.model.validation_scores_ else 0.0
            )
            
            self.logger.info(f"Model trained successfully. Metrics: {metrics}")
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error in model training: {str(e)}")
            raise
            
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Make predictions on new data.
        
        Args:
            X: Feature DataFrame
            
        Returns:
            Array of predictions
        """
        if not self.model or not self.scaler:
            raise ValueError("Model not trained. Call train() first.")
            
        X_scaled = self.scale_features(X, fit=False)
        return self.model.predict(X_scaled)
        
    def save_model(self, filepath: Path) -> None:
        """Save the trained model and scaler.
        
        Args:
            filepath: Path to save the model
        """
        if not self.model:
            raise ValueError("No model to save. Train the model first.")
            
        try:
            import joblib
            save_dict = {
                'model': self.model,
                'scaler': self.scaler,
                'feature_columns': self.feature_columns,
                'config': self.config
            }
            filepath.parent.mkdir(parents=True, exist_ok=True)
            joblib.dump(save_dict, filepath)
            self.logger.info(f"Model saved successfully to {filepath}")
            
        except Exception as e:
            self.logger.error(f"Error saving model: {str(e)}")
            raise
            
    @classmethod
    def load_model(cls, filepath: Path) -> 'NFLPredictor':
        """Load a trained model from file.
        
        Args:
            filepath: Path to the saved model
            
        Returns:
            Loaded NFLPredictor instance
        """
        try:
            import joblib
            save_dict = joblib.load(filepath)
            
            predictor = cls(save_dict['config'])
            predictor.model = save_dict['model']
            predictor.scaler = save_dict['scaler']
            predictor.feature_columns = save_dict['feature_columns']
            
            return predictor
            
        except Exception as e:
            logging.error(f"Error loading model: {str(e)}")
            raise 