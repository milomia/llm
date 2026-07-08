from typing import List, Dict, Optional

from pydantic import BaseModel, Field, field_validator


class StatementParser(BaseModel):
    opening_statements: List[str] = Field(default=[], description="list of different Opening statements")
    questioning_statements: List[str] = Field(default=[], description="list of different Questioning statements")
    presenting_statements: List[str] = Field(default=[], description="list of different Presenting statements")
    closing_outcome_sentences: Optional[List[Dict[str, str]]] = Field(
        default=[],
        description="list of dictionaries (NOT a list of lists) containing closing statement of REP ('closing_statement') and outcome statements OF HCP ('outcome_statement')")

    @field_validator('closing_outcome_sentences', mode='before')
    @classmethod
    def flatten_and_clean_closing(cls, v):
        if not v:
            return []
        # Flatten if LLM double-nested: [[{...}]] -> [{...}]
        if isinstance(v, list) and len(v) > 0 and isinstance(v[0], list):
            v = [item for sublist in v for item in sublist]
        # Replace None values with empty strings
        cleaned = []
        for item in v:
            if isinstance(item, dict):
                cleaned.append({
                    k: (val if val is not None else "")
                    for k, val in item.items()
                })
        return cleaned

class StatementParserWithoutOpening(BaseModel):
    questioning_statements: List[str] = Field(description="list of different Questioning statements")
    presenting_statements: List[str] = Field(description="list of different Presenting statements")
    closing_outcome_sentences: List[Dict[str, str]] = Field(
        description="list of dictionaries containing closing and outcome statements. Example: {'closing_statement': closing_dailouge (REP), 'outcome_statement': outcome_dailouge(HCP)}")


class StatementParserWithoutClosing(BaseModel):
    opening_statements: List[str] = Field(description="list of different Opening statements")
    questioning_statements: List[str] = Field(description="list of different Questioning statements")
    presenting_statements: List[str] = Field(description="list of different Presenting statements")


class StatementParserWithoutOpeningAndClosing(BaseModel):
    questioning_statements: List[str] = Field(description="list of different Questioning statements")
    presenting_statements: List[str] = Field(description="list of different Presenting statements")


class StatementLevelModel(BaseModel):
    id: int = Field(description="the ID of the statement exactly as provided in the input")
    level: Optional[int] = Field(default=0, description="assigned level between 1 and 4, where 1 is lowest and 4 is highest")
    confidence_score: Optional[int] = Field(default=0, description="integer between 0 and 100 representing how confident you are in your level assignment. Must be an integer, never null.")
    reason: str = Field(description="reason for your evaluation in max 1 line")


class EvaluationResult(BaseModel):
    statements: List[StatementLevelModel] = Field(..., description="A list of statement level Model")
