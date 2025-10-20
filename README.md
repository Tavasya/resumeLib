# Resume Library

A FastAPI-based backend for scraping, storing, and querying resumes using Google Custom Search API and Supabase.

## Project Structure

```
resumeLibrary/
├── main.py                 # FastAPI application entry point
├── config/                 # Configuration management
│   ├── __init__.py
│   └── settings.py        # Environment settings
├── api/                   # API endpoints
│   ├── __init__.py
│   └── routes/           # Route handlers
│       └── __init__.py
├── scraper/              # Resume scraping logic (NOT part of API)
│   └── __init__.py
├── services/             # Business logic services
│   └── __init__.py
├── models/               # Pydantic models and schemas
│   └── __init__.py
├── .env                  # Environment variables (not in git)
├── .env.example          # Example environment file
└── requirements.txt      # Python dependencies
```

## Setup

1. **Create virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   - Copy `.env.example` to `.env`
   - Fill in your API keys and credentials

4. **Run the application:**
   ```bash
   python main.py
   ```
   Or with uvicorn directly:
   ```bash
   uvicorn main:app --reload
   ```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8080/docs
- ReDoc: http://localhost:8080/redoc

## Environment Variables

- `SUPABASE_URL` - Your Supabase project URL
- `SUPABASE_KEY` - Supabase secret key
- `GOOGLE_API_KEY` - Google Custom Search API key
- `GOOGLE_CX` - Google Custom Search Engine ID

## Development

The project follows a modular structure:
- **api/** - Contains all API-related code and routes
- **scraper/** - Standalone scraping logic (separate from API)
- **services/** - Business logic and integrations
- **models/** - Data models and schemas
- **config/** - Application configuration
