# NFL Player Performance Predictor

A machine learning system that predicts NFL player performance using historical data from FFToday. The system downloads both projected and actual player statistics, processes the data, and trains neural network models for different positions (QB, RB, WR, TE).

## Features

- Automated data collection from FFToday with ad blocking
- Position-specific neural network models
- Historical data analysis and processing
- Comprehensive error handling and logging
- Command-line interface for training
- Model persistence and versioning

## Project Structure

```
NFL_machinelearn/
├── NFL_machinelearn/
│   ├── config/
│   │   ├── __init__.py
│   │   └── config.py      # Configuration settings
│   ├── data/
│   │   ├── downloaders/   # Data downloading modules
│   │   └── data_manager.py
│   ├── ml/
│   │   └── models/       # ML model definitions
│   ├── utils/
│   │   ├── __init__.py
│   │   └── browser_setup.py
│   └── train.py          # Main training script
├── data/
│   ├── raw/              # Raw downloaded data
│   ├── processed/        # Processed training data
│   └── models/          # Trained models
├── setup.sh             # Automated setup script
├── pyproject.toml       # Project dependencies and metadata
└── README.md
```

## Prerequisites

- Python 3.8 or higher
- Chrome browser installed
- Git (for cloning the repository)

## Setup Instructions

### Option 1: Automated Setup (macOS/Linux)

1. **Clone the Repository**
   ```bash
   git clone https://github.com/JordanLevy99/NFL_machinelearn.git
   cd NFL_machinelearn
   ```

2. **Run Setup Script**
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

   The setup script will:
   - Check Python and Chrome installation
   - Download and configure ChromeDriver
   - Create virtual environment
   - Install dependencies
   - Set up project directories
   - Configure the project

3. **Activate Environment**
   ```bash
   source venv/bin/activate
   ```

4. **Configure Environment Variables**
   Create a `.env` file in the project root with the following variables:
   ```
   FFTODAY_USERNAME=your_username
   FFTODAY_PASSWORD=your_password
   ```

### Option 2: Manual Setup (Windows/Alternative)

1. **Clone the Repository**
   ```bash
   git clone https://github.com/JordanLevy99/NFL_machinelearn.git
   cd NFL_machinelearn
   ```

2. **Create and Activate Virtual Environment**
   ```bash
   # On macOS/Linux
   python -m venv venv
   source venv/bin/activate

   # On Windows
   python -m venv venv
   .\venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -e .
   ```

4. **Download ChromeDriver**
   - Visit [ChromeDriver Downloads](https://sites.google.com/chromium.org/driver/)
   - Download the version matching your Chrome browser
   - Extract the downloaded file

5. **Configure ChromeDriver**
   
   Option 1: Add to System PATH
   - Move chromedriver to a directory in your system PATH
   - Update config/config.py with the path:
     ```python
     CONFIG = {
         ...
         'CHROME_DRIVER_PATH': '/usr/local/bin/chromedriver'  # Example path
     }
     ```
   
   Option 2: Keep in Project Directory
   - Create a 'drivers' directory in your project
   - Move chromedriver there
   - Update config/config.py with relative path:
     ```python
     CONFIG = {
         ...
         'CHROME_DRIVER_PATH': 'drivers/chromedriver'
     }
     ```

</edit>

## Usage

1. **Download and Train Models**
   ```bash
   # Train models for all positions
   python NFL_machinelearn/train.py

   # Train specific positions
   python NFL_machinelearn/train.py --positions QB RB

   # Force new data download
   python NFL_machinelearn/train.py --force-download

   # Specify year range
   python NFL_machinelearn/train.py --start-year 2018 --end-year 2023
   ```

2. **Monitor Training**
   - Check the console output for training progress
   - Logs will show data download status and training metrics
   - Trained models are saved in data/models with timestamps

## Data Sources

The system uses [FFToday](http://www.fftoday.com) for:
- Projected player statistics
- Actual player performance data
- Player information and team assignments

## Model Details

Position-specific neural network configurations:
- QB: 2-layer network [100, 50] neurons
- RB/WR: 2-layer network [120, 60] neurons
- TE: 2-layer network [80, 40] neurons

All models use:
- ReLU activation
- Adam optimizer
- Early stopping
- Feature standardization

## Troubleshooting

1. **ChromeDriver Issues**
   - Ensure Chrome browser and ChromeDriver versions match
   - Verify ChromeDriver is executable (`chmod +x` on Unix systems)
   - Check the path in your `.env` file is correct
   - For automated setup issues, check Chrome version matches downloaded driver

2. **Data Download Problems**
   - Check internet connection
   - Verify FFToday is accessible
   - Check storage permissions in data directory
   - Ensure uBlock Origin extension is properly loaded

3. **Training Issues**
   - Verify sufficient data is available
   - Check memory usage for large datasets
   - Review logs for specific error messages

4. **Setup Script Issues**
   - Make sure script is executable (`chmod +x setup.sh`)
   - Check Python version (`python3 --version`)
   - Verify Chrome installation
   - Check internet connection for downloading dependencies

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- FFToday for providing the data source
- scikit-learn for machine learning tools
- Selenium and BeautifulSoup for web scraping capabilities
- uBlock Origin for ad blocking functionality