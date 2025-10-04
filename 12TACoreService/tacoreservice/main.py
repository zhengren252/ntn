from fastapi import FastAPI

app = FastAPI(title="TACoreService")

@app.get("/health", status_code=200, tags=["Health"])
async def health_check():
    """Provides a simple health check endpoint."""
    return {"status": "healthy"}

# Minimal startup message for logging
@app.on_event("startup")
async def startup_event():
    print("TACoreService application startup successful.")