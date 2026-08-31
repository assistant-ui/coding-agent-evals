"""Structured verdict for one WF-E / WF-T judge call."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class JudgeVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid", exclude_none=True)

    verdict: Literal["pass", "fail", "insufficient_evidence"] = Field(
        ...,
        description="Outcome for this one check: pass, fail, or insufficient_evidence",
    )
    evidence_ids: list[str] = Field(
        ...,
        description="Transcript event IDs copied from the compact transcript",
    )
    reason: str = Field(..., description="At most two short sentences")
