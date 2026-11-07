import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.agents.orchestrator import OrchestratorAgent

app = FastAPI(title="GML AI Business Assistant API", version="1.0.0")
agent = OrchestratorAgent()

class ChatRequest(BaseModel):
    query: str
    session_id: str = "default"

class ChatResponse(BaseModel):
    answer: str
    sql_query: str | None = None
    data: list | None = None
    sources: list[str] | None = None
    intent: str | None = None

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        result = await agent.run(request.query, request.session_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "ok"}
