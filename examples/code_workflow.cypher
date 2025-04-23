// Example workflow demonstrating the code.py utility for executing Python scripts
// Note: Run this script manually in your Neo4j instance

// 1. Create the root step that asks for data to process
CREATE (root:STEP {
  id: "code_root",
  name: "Request Data",
  description: "Request input data for processing",
  function: "utils.request.request",
  input: JSON.stringify({
    "prompt": "Please provide a list of numbers separated by commas:",
    "options": null
  })
})

// 2. Create data preparation step using our code utility
CREATE (prepare:STEP {
  id: "prepare_data",
  name: "Prepare Data",
  description: "Prepares data by parsing the input string",
  function: "utils.code.code",
  input: JSON.stringify({
    "code": `
# Get the user's input
user_input = @{SESSION_ID}.code_root.response

# Parse the comma-separated numbers
numbers = [int(n.strip()) for n in user_input.split(',')]

# Create a structured result
result = {
    "numbers": numbers,
    "count": len(numbers),
    "input_string": user_input
}
`
  })
})

// 3. Create a data analysis step
CREATE (analyze:STEP {
  id: "analyze_data",
  name: "Analyze Data",
  description: "Analyzes the prepared data using Python",
  function: "utils.code.code",
  input: JSON.stringify({
    "code": `
# Get the prepared numbers from the previous step
numbers = @{SESSION_ID}.prepare_data.result.numbers

# Perform various calculations
import statistics
import math

# Basic statistics
result = {
    "input_numbers": numbers,
    "count": len(numbers),
    "sum": sum(numbers),
    "min": min(numbers),
    "max": max(numbers),
    "range": max(numbers) - min(numbers),
    "mean": statistics.mean(numbers) if numbers else 0,
    "median": statistics.median(numbers) if numbers else 0
}

# Add more advanced calculations if we have enough numbers
if len(numbers) > 1:
    result["variance"] = statistics.variance(numbers)
    result["stdev"] = statistics.stdev(numbers)

# Calculate some additional properties
result["is_sorted"] = numbers == sorted(numbers)
result["has_duplicates"] = len(numbers) != len(set(numbers))
result["even_count"] = sum(1 for n in numbers if n % 2 == 0)
result["odd_count"] = sum(1 for n in numbers if n % 2 != 0)
`
  })
})

// 4. Create a visualization step
CREATE (visualize:STEP {
  id: "visualize_data",
  name: "Visualize Data",
  description: "Creates a visualization of the data",
  function: "utils.code.code",
  input: JSON.stringify({
    "code": `
# Get the analyzed data
data = @{SESSION_ID}.analyze_data.result
numbers = data["input_numbers"]

# Generate ASCII chart representation
def generate_ascii_chart(numbers, width=50):
    if not numbers:
        return "No data to visualize"
        
    min_val = min(numbers)
    max_val = max(numbers)
    range_val = max_val - min_val if max_val > min_val else 1
    
    lines = []
    header = f"Data Visualization (min: {min_val}, max: {max_val})"
    lines.append(header)
    lines.append("-" * len(header))
    
    for n in numbers:
        # Calculate bar length proportional to value
        normalized = (n - min_val) / range_val if range_val > 0 else 0.5
        bar_length = int(normalized * width)
        bar = "#" * bar_length
        lines.append(f"{n:4d} | {bar}")
    
    return "\\n".join(lines)

# Generate summary of statistics
def generate_summary(data):
    lines = []
    lines.append("Statistical Summary")
    lines.append("-----------------")
    for key, value in data.items():
        if key != "input_numbers":  # Skip the raw input numbers
            lines.append(f"{key}: {value}")
    
    return "\\n".join(lines)

# Combine visualizations into a result
result = {
    "ascii_chart": generate_ascii_chart(numbers),
    "summary": generate_summary(data),
    "analyzed_data": data
}
`
  })
})

// 5. Create a reply step
CREATE (reply:STEP {
  id: "code_reply",
  name: "Format Reply",
  description: "Formats the final reply with visualization",
  function: "utils.reply.reply",
  input: JSON.stringify({
    "message": "Here's the analysis of your numbers:\n\n```\n@{SESSION_ID}.visualize_data.result.ascii_chart\n```\n\n**Summary:**\n```\n@{SESSION_ID}.visualize_data.result.summary\n```\n\nThank you for using the data analyzer!"
  })
})

// Create the workflow connections
CREATE 
  (root)-[:NEXT]->(prepare),
  (prepare)-[:NEXT]->(analyze),
  (analyze)-[:NEXT]->(visualize),
  (visualize)-[:NEXT]->(reply)

// Log completion
RETURN "Code workflow created successfully with 5 steps" as message 