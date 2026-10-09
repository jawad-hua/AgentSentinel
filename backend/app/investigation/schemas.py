from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Text = Annotated[str, Field(min_length=1, max_length=1200)]
Refs = Annotated[list[str], Field(min_length=1, max_length=12)]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Claim(Strict):
    statement: Text
    evidence_ids: Refs


class Triage(Strict):
    summary: Text
    severity: Literal["low", "medium", "high"]
    affected_node: str | None = Field(max_length=32)
    evidence_ids: Refs
    investigate: bool
    reason: Text


class Diagnosis(Strict):
    hypotheses: list[Claim] = Field(min_length=1, max_length=3)
    missing_evidence: list[Text] = Field(max_length=5)
    next_steps: list[Text] = Field(min_length=1, max_length=5)


class Change(Strict):
    node: str = Field(pattern=r"^node_[0-9]{1,3}$")
    field: Literal["retryOnFail", "maxTries", "waitBetweenTries"]
    value: bool | int


class Fix(Strict):
    disposition: Literal["propose", "no_safe_fix"]
    rationale: Text
    evidence_ids: Refs
    changes: list[Change] = Field(max_length=3)
    verification_plan: list[Text] = Field(min_length=1, max_length=5)

    @model_validator(mode="after")
    def consistent(self):
        if (self.disposition == "propose") != bool(self.changes):
            raise ValueError("Proposal disposition must match its changes")
        return self


class Validation(Strict):
    accepted: bool
    supported_hypotheses: list[int] = Field(max_length=3)
    evidence_ids: Refs
    rationale: Text
    concerns: list[Text] = Field(max_length=6)


class Risk(Strict):
    level: Literal["low", "medium", "high", "blocked"]
    evidence_ids: Refs
    rationale: Text
    hazards: list[Text] = Field(max_length=6)


STAGES = {
    "triage": Triage,
    "diagnosis": Diagnosis,
    "fix": Fix,
    "validator": Validation,
    "risk": Risk,
}


def validate_references(output: BaseModel, facts: list[dict]) -> None:
    known = {fact["id"] for fact in facts}

    def walk(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key == "evidence_ids" and (len(child) != len(set(child)) or set(child) - known):
                    raise ValueError("Invalid evidence references")
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(output.model_dump())
