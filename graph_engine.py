def create_workflow():
    """Create the workflow definition with nodes and edges."""
    
    # Create root node that initializes the workflow
    root = Node(
        id="root",
        function="utils.init_workflow.initialize_workflow",
        input={}
    )
    
    # Request node waits for user message
    request = Node(
        id="request",
        function="utils.user_interaction.get_user_message",
        input={}
    )
    
    # Generation node creates llm response to user message
    generate = Node(
        id="generate",
        function="utils.llm.generate_movie_assistant_response",
        input={
            "message": "@{SESSION_ID}.request.output",
            "function_map": {
                "is_movie_question": "Determine if the user is asking about a movie"
            }
        }
    )
    
    # Movie info node uses Neo4j to get movie information if needed
    movie_info = Node(
        id="movie_info",
        function="utils.cypher.execute_cypher",
        input={
            "instruction": "Get information about the movie Fight Club and its actors",
            "ontology": "The graph database contains the following node types:\n- Movie: Represents a movie with properties title, released, etc.\n- Person: Represents a person with properties name, born, etc.\nRelationships:\n- ACTED_IN: From Person to Movie, indicating an actor appeared in a movie.",
            "session_id": "{SESSION_ID}",
            "title": "Fight Club"  # Add explicit title parameter for debugging
        }
    )
    
    # Reply node sends response back to user
    reply = Node(
        id="reply",
        function="utils.reply.reply",
        input={
            "message": "@{SESSION_ID}.movie_info.overview",  # Prioritize information from the graph
            "llm_response": "@{SESSION_ID}.generate.response",  # Use LLM response as fallback
            "movie_info": "@{SESSION_ID}.movie_info.result"  # Pass the raw Neo4j results for reference
        }
    )
    
    # Define connections between nodes (workflow graph)
    edges = [
        Edge(source=root, target=request),
        Edge(source=request, target=generate),
        
        # Route to movie info if is_movie_question is true
        Edge(
            source=generate,
            target=movie_info,
            conditions=["@{SESSION_ID}.generate.is_movie_question"]
        ),
        
        # Always route to reply, but with optional movie_info attached
        Edge(source=generate, target=reply),
        Edge(source=movie_info, target=reply)
    ]
    
    return Workflow(
        nodes=[root, request, generate, movie_info, reply],
        edges=edges
    ) 