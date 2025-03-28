#!/bin/bash
# Setup script for LUNA on Unix-based systems

# Make sure we're in the right directory
cd "$(dirname "$0")"

echo "Setting up LUNA project..."

# Check if python3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install Python 3 before continuing."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
else
    echo "Virtual environment already exists."
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

echo "Setup complete!"
echo ""
echo "To activate the environment in your terminal, run:"
echo "source venv/bin/activate"
echo ""
echo "To run the project, ensure your .env.local file is set up, then run:"
echo "python main.py --init       # To initialize database schema"
echo "python main.py --create-example   # To create an example workflow"
echo "python main.py --run        # To run the workflow" 