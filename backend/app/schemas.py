from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    database: str


class CategoryCoverage(BaseModel):
    count: int
    percentage: float


class SummaryStatistics(BaseModel):
    avg_score: float
    min_score: int
    max_score: int


class AccessibilitySummaryResponse(BaseModel):
    total_blocks: int
    statistics: SummaryStatistics
    coverage_metrics: dict[str, CategoryCoverage]
    source: str | None = None
    message: str | None = None


class HistogramBucket(BaseModel):
    score: int
    count: int


class HistogramResponse(BaseModel):
    histogram: list[HistogramBucket]
    source: str | None = None


class AccessibilityBlock(BaseModel):
    block_gid: int
    accessibility_score: int
    has_education: int
    has_health: int
    has_shopping: int
    has_recreation: int
    distance_to_network: float | None


class AnalysisRun(BaseModel):
    run_id: int
    run_code: str
    label: str
    city: str
    walking_speed_mps: float
    time_threshold_sec: int
    score_min: int
    score_max: int
    categories: list[str]
    pipeline_version: str
    is_paper_baseline: bool
    result_table: str | None = None
    block_count: int | None = None
    service_count: int | None = None
    avg_score: float | None = None
    notes: str | None = None
    created_at: str | None = None
    api_view: str | None = None


class AnalysisRunsResponse(BaseModel):
    runs: list[AnalysisRun]


class DataQualityCheck(BaseModel):
    check_id: str
    label: str
    value: float | int | str | None
    unit: str | None = None
    severity: str = Field(description="info | warn | critical")


class DataQualityResponse(BaseModel):
    checks: list[DataQualityCheck]


class ScenarioCompareResponse(BaseModel):
    base_run: str
    other_run: str
    total_blocks: int
    improved_blocks: int
    worsened_blocks: int
    unchanged_blocks: int
    avg_score_base: float
    avg_score_other: float
    avg_score_delta: float


class NeighborhoodSummaryItem(BaseModel):
    neighborhood_name: str
    block_count: int
    avg_score: float
    pct_education: float
    pct_health: float
    pct_shopping: float
    pct_recreation: float


class NeighborhoodSummaryResponse(BaseModel):
    available: bool
    neighborhoods: list[NeighborhoodSummaryItem] = []
    message: str | None = None
