"""
main.py - fastapi entry point
mounts all the routers for the pharmacy system
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import settings

# create app
app = FastAPI(
    title="Pharmacy AI System",
    description="HIPAA-safe automation for independent pharmacy",
    version="0.1.0"
)

# cors - allow frontend to talk to us
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# health check
@app.get("/health")
def health():
    return {"status": "ok", "debug": settings.DEBUG}


# mount routers
from handlers import chat, sms, email, voice, analytics
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(sms.router, prefix="/api/sms", tags=["sms"])
app.include_router(email.router, prefix="/api/email", tags=["email"])
app.include_router(voice.router, prefix="/api/voice", tags=["voice"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])


# mount dashboard static files
app.mount("/dashboard", StaticFiles(directory="dashboard", html=True), name="dashboard")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
