from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config import settings
from src.api.routes_events import router as events_router
from src.api.routes_twilio import router as twilio_router
from src.api.routes_hitl import router as hitl_router

app = FastAPI(
    title="HealthFlow AI Orchestration Engine",
    description="Production healthcare pre-admission clearance & post-discharge triage system",
    version="0.1.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(events_router)
app.include_router(twilio_router)
app.include_router(hitl_router)

@app.get("/health")
async def health_check():
    return {
        "status": "HEALTHY",
        "service": "healthflow-ai",
        "environment": settings.ENVIRONMENT,
        "interoperability": "FHIR R4"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
