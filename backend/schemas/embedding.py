from datetime import datetime

from pydantic import BaseModel


class CandidateEmbeddingResponse(BaseModel):
    candidate_id: int
    model_name: str
    dimensions: int
    source_hash: str
    embedded_at: datetime
    stale: bool


class JobEmbeddingResponse(BaseModel):
    job_id: int
    model_name: str
    dimensions: int
    source_hash: str
    embedded_at: datetime
    stale: bool


class SemanticMatchResponse(BaseModel):
    candidate_id: int
    job_id: int
    cosine_similarity: float
    semantic_score: int
    model_name: str
    candidate_source_hash: str
    job_source_hash: str
    calculated_at: datetime
