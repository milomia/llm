from analysis.llm import make_agent
from analysis.models import Transcription
from analysis.outputParser import SentimentResult

MAX_ATTEMPTS = 3

SENTIMENT_PROMPT = (
    "Respond with ONLY a JSON object, no explanation, no markdown, no preamble.\n"
    "The transcript below is a conversation between a representative (REP) and one or more "
    "healthcare professionals (HCPs).\n\n"
    "<transcript>\n{transcript}\n</transcript>\n\n"
    "These are statements made by the REP, each with an id:\n{statements}\n\n"
    "For EVERY statement, find where it occurs in the transcript and judge the sentiment of the HCP's "
    "immediate reaction to it (the HCP's next reply):\n"
    "- positive: interest, agreement, appreciation, willingness to proceed\n"
    "- neutral: acknowledgement or a factual answer with no clear leaning\n"
    "- negative: disagreement, scepticism, objection, disinterest, irritation\n"
    "- no_response: the HCP does not react to this statement\n"
    "Judge the HCP's reaction only, not the tone of the REP's statement.\n\n"
    "For EVERY statement provide id, sentiment, confidence_score (integer 0-100) and reason (max 1 line).\n"
    "Return data matching this shape exactly:\n"
    "{{\"statements\":[{{\"id\":1,\"sentiment\":\"positive\",\"confidence_score\":90,\"reason\":\"short reason\"}}]}}\n"
)


def analyze_sentiment(transcription_id):
    """Stage 3: label the HCP's reaction to each classified REP statement. Idempotent per statement."""
    transcript = Transcription.objects.get(id=transcription_id)
    pending = transcript.statementclassification_set.filter(sentimentDone=False)

    for segment_number in pending.values_list('segment_number', flat=True).distinct().order_by('segment_number'):
        rows = {row.id: row for row in pending.filter(segment_number=segment_number)}
        if not rows or segment_number is None or not 1 <= segment_number <= len(transcript.segments):
            continue

        # The model sometimes drops statements: retry just the ones still unscored.
        remaining = dict(rows)
        for _ in range(MAX_ATTEMPTS):
            if not remaining:
                break
            agent = make_agent(SentimentResult)
            result = agent.run_sync(SENTIMENT_PROMPT.format(
                transcript=transcript.segments[segment_number - 1],
                statements=[{'id': row.id, 'statement': row.statement} for row in remaining.values()],
            ))

            for scored in result.output.statements:
                row = remaining.pop(scored.id, None)
                if row is None:
                    continue
                row.hcp_sentiment = scored.sentiment
                row.hcp_sentiment_confidence = scored.confidence_score
                row.hcp_sentiment_reason = scored.reason
                row.sentimentDone = True
                row.save(update_fields=['hcp_sentiment', 'hcp_sentiment_confidence', 'hcp_sentiment_reason', 'sentimentDone'])

        if remaining:
            print(f"Sentiment: {len(remaining)} statement(s) in segment {segment_number} of transcript "
                  f"{transcription_id} unscored after {MAX_ATTEMPTS} attempts: {sorted(remaining)}")


def get_sentiment_results(transcription_id):
    rows = Transcription.objects.get(id=transcription_id).statementclassification_set.order_by('segment_number', 'id')
    counts = {}
    for row in rows:
        if row.hcp_sentiment:
            counts[row.hcp_sentiment] = counts.get(row.hcp_sentiment, 0) + 1
    return {
        "transcript_id": transcription_id,
        "summary": counts,
        "statements": [
            {
                "id": row.id,
                "category": row.category,
                "segment_number": row.segment_number,
                "statement": row.statement,
                "hcp_sentiment": row.hcp_sentiment,
                "confidence_score": row.hcp_sentiment_confidence,
                "reason": row.hcp_sentiment_reason,
            }
            for row in rows
        ],
    }
