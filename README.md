# Address and GPS Coordinate Lookup Agent

Interactive command-line agent for converting postal addresses into GPS coordinates (geocoding) and vice versa (reverse geocoding).  
It integrates a local language model (Ollama) to intelligently assess the precision of user input, with automatic fallback to heuristic rules when the LLM is unavailable.

---

## Prerequisites

- **Python** 3.9 or higher
- **pip** (Python package manager)
- **[Ollama](https://ollama.com/)** (optional but recommended) with a lightweight model (e.g., `llama3.1:8b`)
- Internet connection to query the Nominatim API (OpenStreetMap)

---

## Installation (Linux)

1. Clone or download the project

```bash
git clone geocoding-agent
cd geocoding-agent
```

1. Create the virtual environment : `python -m venv env`
2. Activate the virtual environment : `source env/bin/activate`
3. Install dependencies : `pip install -r requirements.txt`
4. [Optional] Install and start Ollama

```bash
ollama pull gemma3:1b
ollama serve   # if needed
```

---

## Usage

Run the agent with `python agent.py`.

The agent will prompt you for an address or coordinates:

- Precise address (street, city or street, postal code) → returns GPS coordinates.
- GPS coordinates (e.g., 48.8566, 2.3522) → returns the corresponding address.
- Type `quit` or `q` to exit.

When Ollama is detected, the agent analyzes the input linguistically:

- It detects the language.
- It checks whether the address contains sufficient information.
- If not, it politely asks for clarification.
- Otherwise, it queries the Nominatim API.

If Ollama is not available, heuristic rules (comma detection, postal code, etc.) take over.

---

## Tests

Unit tests use `pytest` and `requests-mock`.  
To run them: `pytest test_agent.py -v`

They cover detection functions, API calls (mocked), and Ollama integration.

---

## Project Structure

```bash
.
├── agent.py              # Main agent script
├── test_agent.py         # Unit tests (pytest)
├── requirements.txt      # Python dependencies
└── README.md             # This file
```

---

## Extending the Project

For better results, you can change prompt or Ollama model by modifying "llm_system_prompt" or "ollama_model" variables (e.g., "mistral", "phi3").

For deployment on a server without a graphical interface, comment out the interactive loop and expose a REST API using FastAPI, for example.

---

## Nominatim API Usage Policy

The Nominatim API is free and open, but relies on reasonable usage. Please:

- Limit requests to 1 per second.
- Provide a custom User-Agent (already configured).
- Do not perform bulk requests without permission.

More information: [https://operations.osmfoundation.org/policies/nominatim/](https://operations.osmfoundation.org/policies/nominatim/)

---

