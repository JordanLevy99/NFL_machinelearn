import os
from pathlib import Path

# Paths
WORKSPACE_ROOT = Path(os.getenv('WORKSPACE_ROOT', os.getcwd()))
DATA_DIR = WORKSPACE_ROOT / 'data'
RAW_DATA_DIR = DATA_DIR / 'raw'
PROCESSED_DATA_DIR = DATA_DIR / 'processed'
MODELS_DIR = DATA_DIR / 'models'
PROJECTIONS_DIR = WORKSPACE_ROOT / 'ML_projections'

# FFToday settings
LEAGUE_ID = '189999'  # Default league ID for FFToday

# Position settings
POSITIONS = {
    'QB': {
        'id': '10',
        'pages': 2,
        'stats': {
            'projected': ['Comp', 'Pass Att', 'Pass Yds', 'Pass TDs', 'Int', 'Rush Att', 'Rush Yds', 'Rush TDs'],
            'actual': ['Comp', 'Pass Att', 'Pass Yds', 'Pass TDs', 'Int', 'Rush Att', 'Rush Yds', 'Rush TDs']
        }
    },
    'RB': {
        'id': '20',
        'pages': 3,
        'stats': {
            'projected': ['Rush Att', 'Rush Yds', 'Rush TDs', 'Rec', 'Rec Yds', 'Rec TDs'],
            'actual': ['Rush Att', 'Rush Yds', 'Rush TDs', 'Rec', 'Rec Yds', 'Rec TDs']
        }
    },
    'WR': {
        'id': '30',
        'pages': 4,
        'stats': {
            'projected': ['Rec', 'Rec Yds', 'Rec TDs'],
            'actual': ['Rec', 'Rec Yds', 'Rec TDs']
        }
    },
    'TE': {
        'id': '40',
        'pages': 3,
        'stats': {
            'projected': ['Rec', 'Rec Yds', 'Rec TDs'],
            'actual': ['Rec', 'Rec Yds', 'Rec TDs']
        }
    }
}

# Required columns for each position
STAT_COLUMNS = {
    'QB': ['Name', 'Team', 'Comp', 'Pass Att', 'Pass Yds', 'Pass TDs', 'Int', 'Rush Att', 'Rush Yds', 'Rush TDs', 'FPts'],
    'RB': ['Name', 'Team', 'Rush Att', 'Rush Yds', 'Rush TDs', 'Rec', 'Rec Yds', 'Rec TDs', 'FPts'],
    'WR': ['Name', 'Team', 'Rec', 'Rec Yds', 'Rec TDs', 'FPts'],
    'TE': ['Name', 'Team', 'Rec', 'Rec Yds', 'Rec TDs', 'FPts']
}

# Model settings
MODEL_PARAMS = {
    'QB': {
        'n_estimators': 100,
        'max_depth': 10,
        'min_samples_split': 5,
        'min_samples_leaf': 2
    },
    'RB': {
        'n_estimators': 100,
        'max_depth': 8,
        'min_samples_split': 4,
        'min_samples_leaf': 2
    },
    'WR': {
        'n_estimators': 100,
        'max_depth': 8,
        'min_samples_split': 4,
        'min_samples_leaf': 2
    },
    'TE': {
        'n_estimators': 100,
        'max_depth': 6,
        'min_samples_split': 4,
        'min_samples_leaf': 2
    }
}

# Feature columns for each position
FEATURE_COLUMNS = {
    'QB': ['Comp', 'Pass Att', 'Pass Yds', 'Pass TDs', 'Int', 'Rush Att', 'Rush Yds', 'Rush TDs'],
    'RB': ['Rush Att', 'Rush Yds', 'Rush TDs', 'Rec', 'Rec Yds', 'Rec TDs'],
    'WR': ['Rec', 'Rec Yds', 'Rec TDs'],
    'TE': ['Rec', 'Rec Yds', 'Rec TDs']
}

# Target column
TARGET_COLUMN = 'FPts' 