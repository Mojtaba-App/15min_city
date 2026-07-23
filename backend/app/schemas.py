from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


class AccessibilitySummary(BaseModel):
    total_blocks: int
    avg_score: float
    min_score: int
    max_score: int


class AccessibilityBlock(BaseModel):
    block_gid: int
    accessibility_score: int
    has_education: int
    has_health: int
    has_shopping: int
    has_recreation: int
    distance_to_network: float | None
