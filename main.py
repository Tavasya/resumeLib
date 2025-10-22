from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from api.routes import resumes, subscriptions, user_resume
from api.routes.webhooks import clerk, stripe

# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Resume Library API - Scrape, store, and query resumes",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://www.cookedcareer.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "status": "running",
        "environment": settings.ENVIRONMENT
    }


@app.get("/health")
async def health():
    """Detailed health check"""
    return {
        "status": "healthy",
        "supabase_configured": bool(settings.SUPABASE_URL and settings.SUPABASE_KEY),
        "google_api_configured": bool(settings.GOOGLE_API_KEY and settings.GOOGLE_CX)
    }


# Include routers
app.include_router(resumes.router, prefix="/api/resumes", tags=["resumes"])
app.include_router(subscriptions.router, prefix="/api/subscriptions", tags=["subscriptions"])
app.include_router(user_resume.router, prefix="/api/user-resume", tags=["user-resume"])

# Webhooks
app.include_router(clerk.router, prefix="/api/webhooks", tags=["webhooks"])
app.include_router(stripe.router, prefix="/api/webhooks", tags=["webhooks"])

# Scraper routes will be added later
# from api.routes import scraper
# app.include_router(scraper.router, prefix="/api/scraper", tags=["scraper"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
