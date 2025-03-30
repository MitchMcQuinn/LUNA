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
    
    # General info node uses different source for non-movie questions
    general_info = Node(
        id="general_info",
        function="utils.search.find_information",
        input={
            "query": "@{SESSION_ID}.request.output"
        }
    )
    
    # Reply node sends response back to user
    reply = Node(
        id="reply",
        function="utils.reply.reply",
        input={
            "message": "@{SESSION_ID}.movie_info.overview",  # Prioritize information from the graph
            "llm_response": "@{SESSION_ID}.generate.response",  # Use LLM response as fallback
            "movie_info": "@{SESSION_ID}.movie_info.result",  # Pass the raw Neo4j results for reference
            "general_info": "@{SESSION_ID}.general_info.result"  # General info for non-movie questions
        }
    )
    
    # Define connections between nodes (workflow graph)
    edges = [
        Edge(source=root, target=request),
        Edge(source=request, target=generate),
        
        # Route to movie info if is_movie_question is true (string format)
        Edge(
            source=generate,
            target=movie_info,
            conditions=["@{SESSION_ID}.generate.is_movie_question"]
        ),
        
        # Route to general info if is_movie_question is false (JSON format)
        Edge(
            source=generate,
            target=general_info,
            conditions=[{"false": "@{SESSION_ID}.generate.is_movie_question"}]
        ),
        
        # Example of complex condition (JSON format with operator)
        # Edge(
        #     source=generate,
        #     target=some_special_step,
        #     conditions=[{
        #         "operator": "AND", 
        #         "true": "@{SESSION_ID}.generate.needs_special_handling",
        #         "false": "@{SESSION_ID}.generate.is_movie_question"
        #     }]
        # ),
        
        # Always route to reply, but with optional movie_info or general_info attached
        Edge(source=generate, target=reply),
        Edge(source=movie_info, target=reply),
        Edge(source=general_info, target=reply)
    ]
    
    return Workflow(
        nodes=[root, request, generate, movie_info, general_info, reply],
        edges=edges
    ) 