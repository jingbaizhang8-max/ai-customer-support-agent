from fastapi import FastAPI

from app.api.agent import router as agent_router
from app.api.tickets import router as tickets_router

app = FastAPI(
    title="AI Customer Support Agent",
    version="0.1.0",
)


app.include_router(
    agent_router,
    prefix="/agent",
    tags=["Agent"],
)

app.include_router(
    tickets_router,
    prefix="/tickets",
    tags=["Tickets"],
)

@app.get("/health")
def health_check():
    return {"status": "ok"}
