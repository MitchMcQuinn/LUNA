"""
API request utility for making external HTTP requests.
"""

import logging
import requests
import os
import json
from urllib.parse import urljoin, quote

# Configure logging
logger = logging.getLogger(__name__)

def api(method="GET", url=None, params=None, headers=None, data=None, json_data=None, auth=None, timeout=30, **kwargs):
    """
    Make an HTTP request to an external API.
    
    Args:
        method: HTTP method (GET, POST, PUT, DELETE, etc.)
        url: The URL to request
        params: Query parameters as a dictionary
        headers: HTTP headers as a dictionary
        data: Request body data (for POST/PUT)
        json_data: JSON request body (alternative to data)
        auth: Authentication tuple (username, password) or object
        timeout: Request timeout in seconds
        **kwargs: Additional parameters for requests library
    
    Returns:
        Dictionary containing:
            - status_code: HTTP status code
            - response: Full response body as text
            - headers: Response headers
            - error: Error message if request failed (optional)
    """
    if not url:
        logger.error("URL is required for API requests")
        return {
            "status_code": 0,
            "response": "",
            "headers": {},
            "error": "URL is required for API requests"
        }
    
    # Sanitize method
    method = method.upper() if method else "GET"
    
    # Process headers - handle environment variables
    processed_headers = {}
    if headers:
        for key, value in headers.items():
            # Handle environment variables in header values
            if isinstance(value, str) and value.startswith("$"):
                env_var = value[1:]
                env_value = os.environ.get(env_var)
                if env_value:
                    processed_headers[key] = env_value
                else:
                    logger.warning(f"Environment variable {env_var} not found for header {key}")
            else:
                processed_headers[key] = value
    
    try:
        logger.info(f"Making {method} request to {url}")
        
        # Make the request
        response = requests.request(
            method=method,
            url=url,
            params=params,
            headers=processed_headers,
            data=data,
            json=json_data,
            auth=auth,
            timeout=timeout,
            **kwargs
        )
        
        # Log the result
        logger.info(f"API request completed with status code {response.status_code}")
        
        # Return the result
        return {
            "status_code": response.status_code,
            "response": response.text,
            "headers": dict(response.headers),
            "error": None if response.ok else f"HTTP Error: {response.status_code} {response.reason}"
        }
        
    except requests.RequestException as e:
        logger.error(f"API request failed: {e}")
        return {
            "status_code": 0,
            "response": "",
            "headers": {},
            "error": str(e)
        }
    except Exception as e:
        logger.error(f"Unexpected error in API request: {e}")
        return {
            "status_code": 0,
            "response": "",
            "headers": {},
            "error": f"Unexpected error: {str(e)}"
        }

# Keep the original request function for backward compatibility
request = api

def get(url, **kwargs):
    """Convenience method for GET requests"""
    return api(method="GET", url=url, **kwargs)
    
def post(url, **kwargs):
    """Convenience method for POST requests"""
    return api(method="POST", url=url, **kwargs)
    
def put(url, **kwargs):
    """Convenience method for PUT requests"""
    return api(method="PUT", url=url, **kwargs)
    
def delete(url, **kwargs):
    """Convenience method for DELETE requests"""
    return api(method="DELETE", url=url, **kwargs) 