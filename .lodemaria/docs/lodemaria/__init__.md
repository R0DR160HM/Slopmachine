# Lodemaria.IA: Chat with an Ollama Model that Can Search the Web

Lodemar.IA is a Python package for interacting with the Ollama model, which allows you to chat with a text-based AI model capable of searching the web. The project is designed to facilitate quick and efficient communication with various knowledge sources.

## Installation
To install Lodemaria.IA using pip:
```bash
pip install lodemaria
```

## Entry Point: `lodemaria.py`
The entry point for Lodemaria.IA is a simple script that runs the main functionality of the library. It can be executed directly with:
```bash
python -m lodemaria
```

### Parameters and Behavior
- **Arguments**:
  - `query`: The question or topic you want to ask the Ollama model about.
- **Output**:
  - A response from the Ollama model, which can include text, links to web pages, or even explanations of complex concepts.

## Public/Exported Classes and Functions
Lodemaria.IA includes several public classes and functions that you can use directly:

### `OllamaClient`
- **Description**: The main class for interacting with the Ollama model.
- **Parameters**:
  - `model`: The name of the Ollama model to use (e.g., "llama2", "codellama").
- **Behavior**:
  - Initializes the connection to the Ollama server.
  - Sends a question to the model and receives the response.

### `OllamaResponse`
- **Description**: A class representing the response from the Ollama model.
- **Parameters**:
  - `text`: The text content of the response.
  - `links` (optional): A list of URLs pointing to web pages mentioned in the response.
- **Behavior**:
  - Provides access to the text and links properties of the response.

## Internal Logic, Algorithms, and Side Effects
Lodemaria.IA leverages several algorithms and internal logic to facilitate seamless communication with the Ollama model. Some notable points include:

### Algorithm:
- **Query Processing**: The package processes user queries by breaking them down into smaller chunks that can be efficiently processed by the Ollama model.
- **Response Generation**: It uses a pre-trained model to generate responses based on the input queries.

### Side Effects:
- **I/O**: When interacting with the Ollama server, this package performs HTTP requests and receives data over the network. This involves establishing connections, sending data, and receiving responses.
- **Global State**: Although not explicitly stated in the documentation, Lodemaria.IA might use global state to manage the model's connection or other settings.

### Example Usage
Here is an example of how you can use Lodemaria.IA to interact with the Ollama model:

```python
from lodemaria import OllamaClient

# Initialize the client with a specific model
client = OllamaClient(model="llama2")

# Send a question to the model
query = "What is the capital of France?"
response = client.send_query(query)

# Print the response
print(response.text)
```

This example demonstrates how to initialize the `OllamaClient`, send a query to the model, and handle the response.
