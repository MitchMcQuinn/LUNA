# Get the input text from the input parameter
input_text = input

# Transform to uppercase
uppercase_text = input_text.upper()

# Create a JSON result with multiple fields
result = {
    "original": input_text,
    "transformed": uppercase_text,
    "length": len(input_text),
    "has_spaces": " " in input_text,
    "word_count": len(input_text.split())
}