from typing import Literal

from pydantic import BaseModel, Field


class AlignmentResult(BaseModel):
    base_id: str
    base_text: str
    ref_id: str | None = None
    ref_text: str | None = None
    diff_type: Literal["same", "fuzzy", "missing"]
    action: str
    reason: str
    confidence: float = Field(ge=0.0, le=1.0)
    source: str
class JudgeVerdict(BaseModel):
    verdict: Literal["same", "modified", "unsure"]
    reason: str
    evidence: str