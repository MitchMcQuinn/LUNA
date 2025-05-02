"""
API request utility for making external HTTP requests.

IMPORTANT: This utility expects input to be provided as a structured JSON object with the following format:
{
    "method": "HTTP_METHOD",  # e.g., "GET", "POST", "PUT", "DELETE"
    "url": "FULL_URL",
    "headers": {
        "Header-Name": "header-value"
    },
    "json_data": {
        "key": "value"
    }
}

All parameters must be specified as key-value pairs within this JSON structure.
The JSON should be provided as a single line without line breaks.
Example single-line format:
{"method": "POST", "url": "https://example.com", "headers": {"Content-Type": "application/json"}, "json_data": {"key": "value"}}
"""

import logging
import requests
import os
import json
from urllib.parse import urljoin, quote

# Configure logging
logger = logging.getLogger(__name__)

def is_nested_session(session_id):
    """Check if a session ID indicates a nested session"""
    # For now, we'll consider sessions created by the create_channel_session step as nested
    # This is a simple heuristic that can be improved
    return session_id and len(session_id) > 20  # Nested sessions tend to have longer IDs

def get_api_url(session_id=None):
    """Get the appropriate API URL based on whether this is a nested session"""
    port = 5001 if is_nested_session(session_id) else 5000
    return f"http://localhost:{port}/api"

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
            - response: Parsed response body as JSON object
            - headers: Response headers
            - error: Error message if request failed (optional)
    """
    if not url:
        logger.error("URL is required for API requests")
        return {
            "status_code": 0,
            "response": None,
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
        # If this is a local API call, use the appropriate port
        if url.startswith("http://localhost:5000/api"):
            # Extract session_id from URL if present
            session_id = None
            if "/session/" in url:
                session_id = url.split("/session/")[1].split("/")[0]
            # Replace with correct port
            base_url = get_api_url(session_id)
            url = url.replace("http://localhost:5000/api", base_url)
        
        logger.info(f"Making {method} request to {url}")
        if json_data:
            logger.info(f"Request JSON data: {json.dumps(json_data)}")
        
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
        
        # Parse the response JSON if content type is JSON
        parsed_response = None
        if 'application/json' in response.headers.get('Content-Type', ''):
            try:
                parsed_response = response.json()
                logger.info(f"Parsed JSON response: {json.dumps(parsed_response)}")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                parsed_response = response.text
        else:
            logger.info(f"Raw response text: {response.text[:1000]}")  # Log first 1000 chars of response
        
        # Create result object
        result = {
            "status_code": response.status_code,
            "response": parsed_response or response.text,
            "headers": dict(response.headers),
            "error": None if response.ok else f"HTTP Error: {response.status_code} {response.reason}"
        }
        
        # Log what we're returning
        logger.info(f"Returning API result: {json.dumps(result)}")
        
        return result
        
    except requests.RequestException as e:
        logger.error(f"API request failed: {e}")
        return {
            "status_code": 0,
            "response": None,
            "headers": {},
            "error": str(e)
        }
    except Exception as e:
        logger.error(f"Unexpected error in API request: {e}")
        return {
            "status_code": 0,
            "response": None,
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