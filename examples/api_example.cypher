// Example workflow demonstrating API utility usage
// This workflow fetches weather data and uses an LLM to extract relevant information

// Clear any existing workflow
MATCH (s:STEP) DETACH DELETE s;

// Create workflow steps
CREATE (root:STEP {
    id: 'root',
    description: 'Root node for API example workflow'
});

CREATE (request_city:STEP {
    id: 'request-city',
    function: 'utils.request.request',
    input: '{"prompt": "Please enter a city name to get the current weather:"}',
    description: 'Get city name from user'
});

CREATE (api_call:STEP {
    id: 'fetch-weather',
    function: 'utils.api.api',
    input: '{"method": "GET", "url": "https://api.openweathermap.org/data/2.5/weather", "params": {"q": "@{SESSION_ID}.request-city.response", "units": "metric", "appid": "$OPENWEATHER_API_KEY"}}',
    description: 'Call OpenWeather API to get weather data'
});

CREATE (process_weather:STEP {
    id: 'process-weather',
    function: 'utils.generate.generate',
    input: '{"model": "gpt-4o", "temperature": 0.7, "system": "You are a helpful weather assistant that provides concise summaries of weather data.", "user": "Here is the raw weather data for @{SESSION_ID}.request-city.response:\\n\\n@{SESSION_ID}.fetch-weather.response\\n\\nPlease provide a friendly, concise summary of the current weather conditions including temperature, humidity, and general conditions. If there was an error fetching the data, please let the user know there was a problem."}',
    description: 'Process weather data with LLM'
});

CREATE (reply_weather:STEP {
    id: 'reply-weather',
    function: 'utils.reply.reply',
    input: '{"message": "@{SESSION_ID}.process-weather.response"}',
    description: 'Reply with weather information'
});

// Create workflow connections
MATCH (root:STEP {id: 'root'})
MATCH (request_city:STEP {id: 'request-city'})
CREATE (root)-[:NEXT]->(request_city);

MATCH (request_city:STEP {id: 'request-city'})
MATCH (api_call:STEP {id: 'fetch-weather'})
CREATE (request_city)-[:NEXT]->(api_call);

MATCH (api_call:STEP {id: 'fetch-weather'})
MATCH (process_weather:STEP {id: 'process-weather'})
CREATE (api_call)-[:NEXT]->(process_weather);

MATCH (process_weather:STEP {id: 'process-weather'})
MATCH (reply_weather:STEP {id: 'reply-weather'})
CREATE (process_weather)-[:NEXT]->(reply_weather); 