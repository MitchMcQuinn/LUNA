"""
Simple Flask application runner for nested sessions with proper path handling
"""

import os
import sys

# Add the LUNA directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(script_dir)

# Now import the Flask app
try:
    from app import app
    print("Starting nested session Flask application...")
    app.run(debug=True, host='0.0.0.0', port=5001)
except Exception as e:
    print(f"Error starting nested session application: {e}")
    import traceback
    traceback.print_exc() 