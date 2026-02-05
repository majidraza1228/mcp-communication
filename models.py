"""Shared Pydantic models for MCP Server-to-Server Communication."""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class AIProcessRequest(BaseModel):
    """Request model for AI processing via Server B's HTTP endpoint."""

    message: str = Field(..., min_length=1, max_length=10000)
    context: Optional[str] = Field(None, max_length=5000, description="System prompt or context")
    model: str = Field("gpt-4", description="OpenAI model to use")
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(1000, ge=1, le=4000)

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "Explain quantum computing in simple terms",
                "context": "You are a helpful science teacher",
                "model": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 500,
            }
        }
    }


class AIUsage(BaseModel):
    """OpenAI API usage information."""

    promptTokens: int
    completionTokens: int
    totalTokens: int
    estimatedCost: float


class AIProcessResponse(BaseModel):
    """Response model from AI processing."""

    status: str
    aiResponse: str
    model: str
    usage: AIUsage
    timestamp: str
    processingTime: float

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "success",
                "aiResponse": "Quantum computing uses quantum mechanical phenomena...",
                "model": "gpt-4",
                "usage": {
                    "promptTokens": 25,
                    "completionTokens": 150,
                    "totalTokens": 175,
                    "estimatedCost": 0.0105,
                },
                "timestamp": "2024-02-04T12:00:00.000Z",
                "processingTime": 2.5,
            }
        }
    }
