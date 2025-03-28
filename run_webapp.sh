#!/bin/bash
# Script to run the Flask web application

# Make sure we're in the right directory
cd "$(dirname "$0")"

# Check if virtual environment exists
if [ -d "venv" ]; then
    # Activate the virtual environment if it exists
    source venv/bin/activate
else
    echo "Virtual environment not found in current directory."
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
fi

# Set debug logging level
export FLASK_DEBUG=1
export PYTHONPATH=$(pwd)
export LOG_LEVEL=DEBUG

echo "Starting Flask application..."
# Run the Flask app directly with more debug info
python app.py 