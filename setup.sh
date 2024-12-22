#!/bin/bash

# Add this at the beginning of the script, right after #!/bin/bash
if [ "$EUID" -eq 0 ]; then 
    echo -e "${RED}[x]${NC} Please do not run this script with sudo"
    echo -e "${YELLOW}[!]${NC} Run it as your normal user: ./setup.sh"
    exit 1
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_message() {
    echo -e "${GREEN}[+]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[x]${NC} $1"
}

# Check if Python 3.8+ is installed
check_python() {
    if command -v python3 >/dev/null 2>&1; then
        python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        major_version=$(echo $python_version | cut -d. -f1)
        minor_version=$(echo $python_version | cut -d. -f2)
        
        if [ "$major_version" -gt 3 ] || ([ "$major_version" -eq 3 ] && [ "$minor_version" -ge 8 ]); then
            print_message "Python $python_version found"
            return 0
        fi
    fi
    print_error "Python 3.8 or higher is required but not found"
    return 1
}

# Check if Chrome is installed
check_chrome() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if [ -d "/Applications/Google Chrome.app" ]; then
            print_message "Google Chrome found"
            return 0
        fi
    else
        # Linux
        if command -v google-chrome >/dev/null 2>&1; then
            print_message "Google Chrome found"
            return 0
        fi
    fi
    print_error "Google Chrome is required but not found"
    return 1
}

# Get Chrome version and download matching ChromeDriver
setup_chromedriver() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # Check if Homebrew is installed
        if ! command -v brew >/dev/null 2>&1; then
            print_error "Homebrew is required but not found. Please install from https://brew.sh"
            return 1
        fi
        
        print_message "Installing ChromeDriver via Homebrew"
        
        # Update Homebrew
        print_message "Updating Homebrew..."
        brew update
        
        # Install or upgrade chromedriver
        if brew list --formula | grep -q "^chromedriver\$"; then
            print_message "Upgrading ChromeDriver..."
            brew upgrade chromedriver
        else
            print_message "Installing ChromeDriver..."
            brew install chromedriver
        fi
        
        # Create drivers directory and symlink
        mkdir -p drivers
        chromedriver_path=$(brew --prefix chromedriver)/bin/chromedriver
        ln -sf "$chromedriver_path" drivers/chromedriver
        
        print_message "ChromeDriver setup complete"
        print_message "ChromeDriver path: $chromedriver_path"
        
    else
        # Linux
        chrome_version=$(google-chrome --version | cut -d " " -f 3)
        print_message "Chrome version: $chrome_version"
        
        # Create drivers directory
        mkdir -p drivers
        
        # Get the latest stable version from the new Chrome for Testing JSON endpoint
        latest_versions_url="https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json"
        print_message "Fetching latest versions from: $latest_versions_url"
        
        if ! latest_versions=$(curl -s "$latest_versions_url"); then
            print_error "Failed to fetch versions information"
            return 1
        fi
        
        platform="linux64"
        
        # Extract the latest stable version that has chromedriver
        if ! driver_version=$(echo "$latest_versions" | python3 -c '
import json, sys
data = json.load(sys.stdin)
versions = data.get("versions", [])
for version in versions:
    if (version.get("channel") == "stable" and 
        any(d.get("platform") == sys.argv[1] for d in version.get("downloads", {}).get("chromedriver", []))):
        print(version.get("version"))
        break
' "$platform"); then
            print_error "Failed to parse version information"
            return 1
        fi
        
        if [ -z "$driver_version" ]; then
            print_error "No suitable ChromeDriver version found"
            return 1
        fi
        
        print_message "Found matching ChromeDriver version: $driver_version"
        
        # Construct download URL
        download_url="https://storage.googleapis.com/chrome-for-testing-public/${driver_version}/chromedriver-${platform}.zip"
        print_message "Downloading from: $download_url"
        
        # Download ChromeDriver
        if ! curl -L --fail --silent --output drivers/chromedriver.zip "$download_url"; then
            print_error "Failed to download ChromeDriver"
            return 1
        fi
        
        # Extract ChromeDriver
        if ! unzip -o -q drivers/chromedriver.zip -d drivers/; then
            print_error "Failed to extract ChromeDriver"
            rm -f drivers/chromedriver.zip
            return 1
        fi
        
        # Move chromedriver to the correct location
        if [ -f "drivers/chromedriver-${platform}/chromedriver" ]; then
            mv "drivers/chromedriver-${platform}/chromedriver" drivers/
            rm -rf "drivers/chromedriver-${platform}"
        fi
        
        # Clean up
        rm -f drivers/chromedriver.zip
        
        # Make ChromeDriver executable
        if [ -f "drivers/chromedriver" ]; then
            chmod +x drivers/chromedriver
            print_message "ChromeDriver setup complete"
        else
            print_error "ChromeDriver file not found after extraction"
            return 1
        fi
    fi
}

# Setup virtual environment and install dependencies
setup_venv() {
    print_message "Creating virtual environment"
    # Remove existing venv if it exists
    if [ -d "venv" ]; then
        print_warning "Removing existing virtual environment"
        rm -rf venv
    fi
    
    python3 -m venv venv
    
    # Ensure correct ownership of the venv directory
    if [ -d "venv" ]; then
        print_message "Setting correct permissions for virtual environment"
        chmod -R u+w venv
    fi
    
    print_message "Activating virtual environment"
    source venv/bin/activate
    
    print_message "Installing dependencies"
    pip install --upgrade pip
    pip install -r requirements.txt
    
    print_message "Installing package in development mode"
    pip install -e .
}

# Create necessary directories
create_directories() {
    print_message "Creating project directories"
    mkdir -p data/raw data/processed data/models
    chmod -R u+w data
}

# Update config file with ChromeDriver path
update_config() {
    print_message "Updating config file"
    config_dir="config"
    mkdir -p "$config_dir"
    
    # Get ChromeDriver path
    if [[ "$OSTYPE" == "darwin"* ]]; then
        chromedriver_path=$(brew --prefix chromedriver)/bin/chromedriver
    else
        chromedriver_path=$(pwd)/drivers/chromedriver
    fi
    
    cat > "$config_dir/config.py" << EOL
# Create a config.py file for shared constants
CONFIG = {
    'POSITIONS': {
        10: ['QB', 12, 13, 2],
        20: ['RB', 10, 12, 3],
        30: ['WR', 10, 12, 3],
        40: ['TE', 7, 9, 3]
    },
    'BASE_URL': 'http://www.fftoday.com',
    'CHROME_DRIVER_PATH': '${chromedriver_path}'
}
EOL
}

# Main setup process
main() {
    print_message "Starting setup process..."
    
    # Check requirements
    check_python || exit 1
    check_chrome || exit 1
    
    # Run setup steps
    setup_chromedriver
    setup_venv
    create_directories
    update_config
    
    print_message "Setup complete! You can now run the training script:"
    print_message "source venv/bin/activate"
    print_message "python src/train.py --help"
}

# Run main setup
main 