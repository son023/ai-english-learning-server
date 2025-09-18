# AI English Learning Server

A basic FastAPI server for English learning applications.

## Features

- User management (create, read users)
- Word dictionary with meanings and examples
- Word search functionality
- Random word learning endpoint
- Basic chat endpoint
- Health check endpoint
- Interactive API documentation

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd ai-english-learning-server
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
```

3. Activate the virtual environment:
- On Windows:
```bash
venv\Scripts\activate
```
- On macOS/Linux:
```bash
source venv/bin/activate
```

4. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Server

Start the server with:
```bash
python main.py
```

Or using uvicorn directly:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The server will be available at: http://localhost:8000

## API Documentation

Once the server is running, you can access:
- Interactive API docs (Swagger UI): http://localhost:8000/docs
- Alternative API docs (ReDoc): http://localhost:8000/redoc

## API Endpoints

### Basic Endpoints
- `GET /` - Welcome message
- `GET /health` - Health check

### User Management
- `POST /users` - Create a new user
- `GET /users` - Get all users
- `GET /users/{user_id}` - Get a specific user

### Word Dictionary
- `GET /words` - Get all words
- `GET /words/{word_id}` - Get a specific word
- `POST /words` - Add a new word
- `GET /words/search/{search_term}` - Search words

### Learning
- `GET /learn/random-word` - Get a random word for learning
- `POST /chat` - Basic chat endpoint

## Example Usage

### Creating a User
```bash
curl -X POST "http://localhost:8000/users" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "John Doe",
       "email": "john@example.com",
       "level": "beginner"
     }'
```

### Getting a Random Word
```bash
curl -X GET "http://localhost:8000/learn/random-word"
```

### Searching Words
```bash
curl -X GET "http://localhost:8000/words/search/hello"
```

## Development

This is a basic implementation using in-memory storage. For production use, consider:
- Adding a proper database (PostgreSQL, MongoDB, etc.)
- Implementing authentication and authorization
- Adding data validation and error handling
- Integrating with AI services for enhanced learning features
- Adding logging and monitoring

## Technologies Used

- FastAPI - Modern, fast web framework for building APIs
- Pydantic - Data validation using Python type hints
- Uvicorn - ASGI server for running FastAPI applications