"""First HTTP API for this repo.

Run with:  uvicorn main:app --reload
Docs at:   http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI

app = FastAPI(
    title="fabric-chaos-sentry API",
    description="Local hello-world. Not wired to the NVIDIA Air fabric yet.",
    version="0.1.0",
)


@app.get("/")
def root():
    """Browser-friendly landing. Returns JSON like every other route."""
    return {
        "message": "API is up",
        "try_next": ["/health", "/docs"],
    }


@app.get("/health")
def health():
    """The shape every real service eventually needs: am I alive?"""
    return {"status": "ok"}
