"""
This is a patch for LUNA/app.py to properly display greeting messages.
Apply the changes below to your app.py file.
"""

# In the /api/session route, modify the code that returns the response:

"""
Replace this code:

return jsonify({
    'session_id': session_id,
    'status': status,
    'messages': messages,
    'awaiting_input': awaiting_input
})

With:
"""

# Add this right after finding awaiting_input:
if awaiting_input and 'prompt' in awaiting_input:
    # Create a greeting message if one doesn't exist already
    greeting_exists = False
    for msg in messages:
        if msg.get('role') == 'assistant':
            greeting_exists = True
            break
            
    if not greeting_exists:
        # Add the greeting to messages
        greeting = {
            'role': 'assistant',
            'content': awaiting_input['prompt']
        }
        messages.append(greeting)
        
        # Update session state with the greeting message
        def update_greeting(current_state):
            if 'messages' not in current_state['data']:
                current_state['data']['messages'] = []
            current_state['data']['messages'].append(greeting)
            return current_state
            
        session_manager.update_session_state(session_id, update_greeting)
        logger.info(f"Added greeting message: {awaiting_input['prompt']}")

return jsonify({
    'session_id': session_id,
    'status': status,
    'messages': messages,
    'awaiting_input': awaiting_input
})


# Similarly, in the /api/session/<session_id>/message route:

"""
Replace this code at the end of the route:

return jsonify({
    'session_id': session_id,
    'status': status,
    'messages': messages,
    'awaiting_input': awaiting_input
})

With:
"""

# Add this right after finding awaiting_input:
if awaiting_input and 'prompt' in awaiting_input and awaiting_input['prompt']:
    # Check if this prompt is already in messages
    prompt_exists = False
    for msg in messages:
        if msg.get('role') == 'assistant' and msg.get('content') == awaiting_input['prompt']:
            prompt_exists = True
            break
            
    if not prompt_exists:
        # Add the followup question to messages
        followup = {
            'role': 'assistant',
            'content': awaiting_input['prompt']
        }
        messages.append(followup)
        
        # Update session state with the followup message
        def update_followup(current_state):
            if 'messages' not in current_state['data']:
                current_state['data']['messages'] = []
            current_state['data']['messages'].append(followup)
            return current_state
            
        session_manager.update_session_state(session_id, update_followup)
        logger.info(f"Added followup message: {awaiting_input['prompt']}")

return jsonify({
    'session_id': session_id,
    'status': status,
    'messages': messages,
    'awaiting_input': awaiting_input
}) 