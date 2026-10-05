from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import time
from app.models import AgentRequest, AgentResponse
from app.agent import Agent


app = FastAPI(title="Clinic Front Desk Agent")

# Configure CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize agent
agent = Agent()


@app.post("/agent/run", response_model=AgentResponse)
async def agent_run(request: AgentRequest) -> AgentResponse:
    """
    Run the clinic front desk agent on a conversation.
    
    Request:
    {
        "conversation_id": "cv_0001",
        "today": "2026-10-01",
        "turns": ["Namaste, Dr. Rao ke saath appointment chahiye tha.", "Kal subah ho jayega?"]
    }
    
    Response:
    {
        "conversation_id": "cv_0001",
        "tool_calls": [...],
        "terminal_state": "booked|rescheduled|cancelled|escalated|refused|abandoned",
        "escalation_reason": "...|null",
        "patient_id": "...|null",
        "appointment_id": "...|null",
        "reply": "...",
        "metrics": {...}
    }
    """
    try:
        start_time = time.time()
        
        # Run the agent
        response = agent.run(request.conversation_id, request.today, request.turns)
        
        # Update metrics
        latency_ms = int((time.time() - start_time) * 1000)
        response.metrics.latency_ms = latency_ms
        
        return response
    except Exception as e:
        # Return an error response
        return AgentResponse(
            conversation_id=request.conversation_id,
            terminal_state="abandoned",
            reply=f"Error: {str(e)}",
            metrics={"turns": len(request.turns), "tokens": 0, "latency_ms": 0}
        )


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
