from pydantic_ai import Agent
from pydantic_ai.models.ollama import OllamaModel
from pydantic_ai.providers.ollama import OllamaProvider
from pydantic_ai.output import NativeOutput

from analysis.aiService.constants import get_important_note
from analysis.models import StatementClassificationTypePrompt
from analysis.outputParser import StatementParser, StatementParserWithoutOpening, StatementParserWithoutClosing, \
    StatementParserWithoutOpeningAndClosing


def create_overlapping_segments(text, seg_length, overlap):
    # Split the text into words
    words = text.split()

    # Initialize segments and start position
    segments = []
    start = 0

    # Loop through the text and create segments
    while start < len(words):
        # End position is start plus segment length
        end = start + seg_length

        # Append the segment from start to end
        segments.append(' '.join(words[start:end]))

        # Update start position with segment length minus overlap
        start += (seg_length - overlap)

    return segments


def get_statements_data(part, total_parts):
    statement_types = StatementClassificationTypePrompt.objects.filter(active=True).order_by("id")
    total_types = []
    final_prompt = ""
    for statement_type in statement_types:
        if (total_parts == 2):
            if(part == 2) and (statement_type.category == "OPENING"):
                continue
            if (part == 1) and (statement_type.category == "CLOSING_OUTCOME"):
                continue
        if(total_parts >= 3 and (((part) * 1.0) / total_parts > .3)) and (statement_type.category == "OPENING"):
            continue
        if(total_parts >= 3 and (((part) * 1.0) / total_parts < .7)) and (statement_type.category == "CLOSING_OUTCOME"):
            continue

        print(statement_type.category)
        total_types.append(statement_type.category)
        final_prompt += "\n-----------for "+statement_type.category+" statements -----------\n"
        prompt_value = (
            f" category: {statement_type.category} , where "
            f"the definition of the {statement_type.category} category: ###{statement_type.definition}### \n\n"
            f"the examples of the {statement_type.category} category: ###{statement_type.examples}### \n\n"
            f"the examples that doesn't belong to {statement_type.category} category: "
            f"###{statement_type.invalid_examples}### \n"
        )
        final_prompt += "'''" + str(prompt_value) + "'''"

    return total_types, final_prompt


def get_important_note_and_parser(total_type_considered, segment, total_segments):
    important_note = get_important_note(not_included_statements="")
    
    # Create pydantic_ai Agent with OllamaModel
    model = OllamaModel(
        'llama3',
        provider=OllamaProvider(base_url='http://localhost:11434/v1')
    )
    
    # Determine which parser model to use based on statement types
    if "OPENING" not in total_type_considered and "CLOSING_OUTCOME" not in total_type_considered:
        agent = Agent(model, output_type=NativeOutput(StatementParserWithoutOpeningAndClosing))
        important_note = get_important_note(not_included_statements="EXTREME_END")
    elif "OPENING" not in total_type_considered:
        agent = Agent(model, output_type=NativeOutput(StatementParserWithoutOpening))
        important_note = get_important_note(not_included_statements="OPENING")
    elif "CLOSING_OUTCOME" not in total_type_considered:
        agent = Agent(model, output_type=NativeOutput(StatementParserWithoutClosing))
        important_note = get_important_note(not_included_statements="CLOSING")
    else:
        agent = Agent(model, output_type=NativeOutput(StatementParser))

    return important_note, agent
