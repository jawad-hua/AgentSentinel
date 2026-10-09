from pydantic import BaseModel, ConfigDict, Field


class HeartbeatInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    workflow_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")
    execution_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")
