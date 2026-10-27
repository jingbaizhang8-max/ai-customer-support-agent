import os
from app.graph.agent_graph import run_graph_agent

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials,
)
from pydantic import BaseModel, Field, ConfigDict

from app.core.auth import verify_access_token
from app.agent.agent_loop import run_agent_loop

router = APIRouter()

bearer_scheme = HTTPBearer(auto_error=False)

class AgentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=2000)

def get_authenticated_customer_id(
        credentials: HTTPAuthorizationCredentials | None = Depends(
            bearer_scheme
        ),
) -> str:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return verify_access_token(credentials.credentials)

@router.post("/chat")
def chat_with_agent(
        request: AgentRequest,
        customer_id: str = Depends(get_authenticated_customer_id),
):

    use_langgraph = (
        os.getenv("USE_LANGGRAPH_AGENT", "false").lower()
        == "true"
    )

    agent_function = (
        run_graph_agent
        if use_langgraph
        else run_agent_loop
    )

    return agent_function(
        user_message=request.message,
        authenticated_customer_id=customer_id,
    )