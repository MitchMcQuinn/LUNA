// Example workflow demonstrating chained API calls
// This workflow gets a GitHub username, fetches their profile, then gets their repositories

// Clear any existing workflow
MATCH (s:STEP) DETACH DELETE s;

// Create workflow steps
CREATE (root:STEP {
    id: 'root',
    description: 'Root node for chained API example workflow'
});

CREATE (request_username:STEP {
    id: 'request-username',
    function: 'utils.request.request',
    input: '{"prompt": "Please enter a GitHub username:"}',
    description: 'Get GitHub username from user'
});

CREATE (fetch_profile:STEP {
    id: 'fetch-profile',
    function: 'utils.api.api',
    input: '{"method": "GET", "url": "https://api.github.com/users/@{SESSION_ID}.request-username.response", "headers": {"Accept": "application/vnd.github.v3+json", "User-Agent": "LUNA-Workflow"}}',
    description: 'Fetch GitHub user profile'
});

CREATE (fetch_repos:STEP {
    id: 'fetch-repos',
    function: 'utils.api.api',
    input: '{"method": "GET", "url": "@{SESSION_ID}.fetch-profile.response|$.repos_url", "headers": {"Accept": "application/vnd.github.v3+json", "User-Agent": "LUNA-Workflow"}}',
    description: 'Fetch user repositories using URL from profile response'
});

CREATE (process_github_data:STEP {
    id: 'process-github-data',
    function: 'utils.generate.generate',
    input: '{"model": "gpt-4o", "temperature": 0.7, "system": "You are a helpful assistant that provides concise summaries of GitHub profile information.", "user": "Here is the GitHub profile data for @{SESSION_ID}.request-username.response:\\n\\nProfile:\\n@{SESSION_ID}.fetch-profile.response\\n\\nRepositories:\\n@{SESSION_ID}.fetch-repos.response\\n\\nPlease provide a friendly, concise summary of this GitHub user including their name, bio, location, number of public repositories, and highlight their 3-5 most interesting repositories (based on stars, forks, or recent activity). If there was an error fetching the data, please let the user know there was a problem."}',
    description: 'Process GitHub data with LLM'
});

CREATE (reply_github:STEP {
    id: 'reply-github',
    function: 'utils.reply.reply',
    input: '{"message": "@{SESSION_ID}.process-github-data.response"}',
    description: 'Reply with GitHub profile information'
});

// Create workflow connections
MATCH (root:STEP {id: 'root'})
MATCH (request_username:STEP {id: 'request-username'})
CREATE (root)-[:NEXT]->(request_username);

MATCH (request_username:STEP {id: 'request-username'})
MATCH (fetch_profile:STEP {id: 'fetch-profile'})
CREATE (request_username)-[:NEXT]->(fetch_profile);

MATCH (fetch_profile:STEP {id: 'fetch-profile'})
MATCH (fetch_repos:STEP {id: 'fetch-repos'})
CREATE (fetch_profile)-[:NEXT]->(fetch_repos);

MATCH (fetch_repos:STEP {id: 'fetch-repos'})
MATCH (process_github_data:STEP {id: 'process-github-data'})
CREATE (fetch_repos)-[:NEXT]->(process_github_data);

MATCH (process_github_data:STEP {id: 'process-github-data'})
MATCH (reply_github:STEP {id: 'reply-github'})
CREATE (process_github_data)-[:NEXT]->(reply_github); 