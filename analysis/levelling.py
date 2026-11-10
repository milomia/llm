from analysis.llm import make_agent
from analysis.models import StatementClassification, FinalStatementWithLevel
from analysis.outputParser import EvaluationResult

MAX_ATTEMPTS = 3

LEVEL_PROMPT = (
    "{category} statements: \n{statements}\n\n"
    "Objective: !!!{objective}!!!\n\n"
    "Evaluation Criteria:\n ###{evaluation_criteria}###\n\n"
    "Score assignment criteria:\n ###{score_assignment_criteria}###\n\n"
    "Instruction:\n ###{instruction}###\n\n"
    "Examples:\n ###{examples}###\n\n"
    "notes:\n ###{notes}###\n\n"
    "CRITICAL: For EVERY statement you MUST provide:\n"
    "- level: integer 1-4 based on score assignment criteria\n"
    "- confidence_score: integer 0-100 representing how certain you are about YOUR level assignment. "
    "This is NOT the quality score — it is YOUR confidence in the level you assigned. "
    "A level 1 statement can still have confidence_score of 90 if you are certain it is level 1.\n"
    "- reason: max 1 line explaining the level assignment\n\n"
    "Return data matching this shape exactly:\n"
    "{{\"statements\":[{{\"id\":1,\"level\":1,\"confidence_score\":90,\"reason\":\"short reason\"}}]}}\n"
)


def level_category(category, transcription, statement_level_obj, parent_span=None):
    """Level every not-yet-levelled statement of one category. The model sometimes drops statements,
    so only the unscored ones are re-asked (up to MAX_ATTEMPTS). Statements still unscored afterwards
    keep levelDone=False so a later run picks them up. Returns the ids left unscored."""
    pending = {
        row.id: row for row in
        transcription.statementclassification_set.filter(category=category, levelDone=False)
    }

    for _ in range(MAX_ATTEMPTS):
        if not pending:
            break
        span = parent_span.span(name="agent_levelling") if parent_span else None
        result = make_agent(EvaluationResult).run_sync(LEVEL_PROMPT.format(
            category=category,
            statements=[{'id': row.id, 'statement': row.statement} for row in pending.values()],
            objective=statement_level_obj.objective,
            evaluation_criteria=statement_level_obj.evaluation_criteria,
            score_assignment_criteria=statement_level_obj.score_assignment_criteria,
            instruction=statement_level_obj.instruction,
            examples=statement_level_obj.examples,
            notes=statement_level_obj.notes,
        ))
        response = result.output
        if span:
            span.end(output=str(response), metadata={"category": category, "num_statements": len(pending)})

        for scored in response.statements:
            row = pending.pop(scored.id, None)
            if row is None:
                continue
            FinalStatementWithLevel.objects.create(
                transcription=transcription,
                category=category,
                statement=row.statement,
                level=scored.level,
                confidence_score=scored.confidence_score,
                reason_for_level=scored.reason,
            )
            StatementClassification.objects.filter(id=row.id).update(levelDone=True)

    if pending:
        print(f"Levelling: {len(pending)} {category} statement(s) of transcript {transcription.id} "
              f"unscored after {MAX_ATTEMPTS} attempts: {sorted(pending)}")
    return sorted(pending)
