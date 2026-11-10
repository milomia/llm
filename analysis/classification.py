from analysis.models import StatementClassification
from analysis.utils import get_statements_data, get_important_note_and_parser, clear_previous_results

CLASSIFICATION_PROMPT = (
    "Respond with ONLY a JSON object, no explanation, no markdown, no preamble. "
    "Return ONLY valid JSON. Do not include explanations, markdown, or extra text. "
    "READ THE {part} PART OF THE TRANSCRIPT (WHOLE TRANSCRIPT HAS TOTAL {total_parts}"
    " PARTS, with overlaps of 200 words in each part).\n"
    " CRITICAL: Copy each statement EXACTLY as it appears in the transcript. "
    "Do NOT paraphrase, summarise, truncate, or add ellipsis (...). "
    "The conversation is between a representative (REP) and one or more healthcare professionals (HCPs). "
    "\nRead the transcript part line by line:\n<transcript>\n{transcript}\n</transcript>\n\n"
    "Objective: Review and classify dialogues from interactions between pharmaceutical sales representatives (REPs) and healthcare professionals (HCPs)."
    " Each dialogue may belong to MORE THAN ONE OR NONE of the following categories( based on its content, intention and definition of the category):\n"
    "{categories}\n"
    " This requires discerning the REP's strategic approach towards initiating the conversation,"
    " engaging in inquiry, presenting information, and steering towards a productive conclusion."
    "\n\nDetailed Definition for Classification::\n"
    "\n{different_statement_definition}\n\n"
    "Important Notes:\n"
    "###{important_note}\n\n"
    "Maintain the original transcript form for authenticity, "
    "focusing on the accuracy and relevance of each classification.###\n\n"
    "Assignment Execution: ### Thoroughly proceed through the transcripts,"
    " identifying and classifying each of REP dialogues according to the category's definition, category's examples and category's invalid examples."
    "Also take care of the guidelines and notes provided. Utilize a nuanced approach to determine the strategic intent "
    "and outcome of the dialogue within the structured interaction framework.###"
)

# Category -> field on the StatementParser* output models. A parser that excludes a category has no such field.
CATEGORY_FIELDS = {
    'OPENING': 'opening_statements',
    'QUESTIONING': 'questioning_statements',
    'PRESENTING': 'presenting_statements',
    'CLOSING_OUTCOME': 'closing_outcome_sentences',
}


def classify_transcription(transcription, trace=None):
    """Stage 1 for one transcript: replace its earlier results, then classify every segment and save
    the statements as StatementClassification rows. Shared by the /classification/ view, the Celery
    task and the sync pipeline. `trace` is an optional Langfuse trace; the caller ends it.
    Returns the number of segments processed."""
    clear_previous_results(transcription)
    total_segments = len(transcription.segments)

    for part, segment in enumerate(transcription.segments, start=1):
        segment_span = trace.span(
            name=f"segment_{part}",
            metadata={"segment_index": part, "total_segments": total_segments},
        ) if trace else None

        categories, definitions = get_statements_data(part, total_segments, segment)
        important_note, agent = get_important_note_and_parser(categories, part, total_segments)

        agent_span = segment_span.span(name="agent_classification") if segment_span else None
        response = agent.run_sync(CLASSIFICATION_PROMPT.format(
            part=part,
            total_parts=total_segments,
            transcript=segment,
            categories=", ".join(categories),
            different_statement_definition=definitions,
            important_note=important_note,
        )).output
        print(response)
        if agent_span:
            agent_span.end(
                output=str(response),
                metadata={"statement_types": categories, "segment_length": len(segment)},
            )

        StatementClassification.objects.bulk_create([
            StatementClassification(
                category=category,
                transcription=transcription,
                statement=str(statement),
                segment_number=part,
            )
            for category, field in CATEGORY_FIELDS.items()
            for statement in getattr(response, field, None) or []
        ])

        if segment_span:
            segment_span.end()

    return total_segments
