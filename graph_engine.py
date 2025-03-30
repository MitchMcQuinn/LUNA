import threading

# Lock for thread safety
workflow_lock = threading.Lock()

# Remove the entire movie-specific workflow creation function
# // ... existing code ... 