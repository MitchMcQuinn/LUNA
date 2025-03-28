"""
Simple Flask application runner with proper path handling
"""

import os
import sys

# Add the LUNA directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(script_dir)

# Now import the Flask app
try:
    from app import app
    print("Starting Flask application...")
    app.run(debug=True, host='0.0.0.0', port=5000)
except Exception as e:
    print(f"Error starting application: {e}")
    import traceback
    traceback.print_exc() 