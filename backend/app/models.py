from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class Turn(BaseModel):
    """A single turn in a conversation."""
    role: str = Field(..., description="'caller' or 'agent'")
    text: str = Field(..., description="The utterance text")


class AgentRequest(BaseModel):
    """Request to the agent."""
    conversation_id: str = Field(..., description="Unique conversation identifier")
    today: str = Field(..., description="Current date in YYYY-MM-DD format")
    turns: List[str] = Field(..., description="Conversation turns")


class ToolCall(BaseModel):
    """A tool call made by the agent."""
    name: str = Field(..., description="Tool name")
    arguments: Dict[str, Any] = Field(..., description="Tool arguments")


class Metrics(BaseModel):
    """Metrics for this conversation."""
    turns: int = Field(..., description="Number of turns")
    tokens: int = Field(default=0, description="Approximate tokens used")
    latency_ms: int = Field(default=0, description="Latency in milliseconds")


class AgentResponse(BaseModel):
    """Response from the agent."""
    conversation_id: str = Field(..., description="Echo of request conversation_id")
    tool_calls: List[ToolCall] = Field(default_factory=list, description="Tools actually called")
    terminal_state: str = Field(..., description="One of: booked, rescheduled, cancelled, escalated, refused, abandoned")
    escalation_reason: Optional[str] = Field(default=None, description="Required when terminal_state is 'escalated'")
    patient_id: Optional[str] = Field(default=None, description="The patient involved, if any")
    appointment_id: Optional[str] = Field(default=None, description="The appointment involved, if any")
    reply: str = Field(..., description="Agent's final response to the caller")
    metrics: Metrics = Field(default_factory=lambda: Metrics(turns=0), description="Performance metrics")
