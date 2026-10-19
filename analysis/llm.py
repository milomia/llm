import os

from pydantic_ai.models import Model


def get_llm_model() -> Model:
    """Return the pydantic_ai model for the configured provider.

    LLM_PROVIDER=ollama (default) | bedrock
    Bedrock uses the standard AWS credential chain (env vars, profile, or role).
    """
    provider = os.getenv('LLM_PROVIDER', 'ollama').lower()

    if provider == 'bedrock':
        from pydantic_ai.models.bedrock import BedrockConverseModel
        from pydantic_ai.providers.bedrock import BedrockProvider

        return BedrockConverseModel(
            os.getenv('BEDROCK_MODEL_ID', 'us.anthropic.claude-haiku-4-5-20251001-v1:0'),
            provider=BedrockProvider(region_name=os.getenv('AWS_REGION', 'us-east-1')),
        )

    from pydantic_ai.models.ollama import OllamaModel
    from pydantic_ai.providers.ollama import OllamaProvider

    return OllamaModel(
        os.getenv('OLLAMA_MODEL', 'llama3'),
        provider=OllamaProvider(base_url=os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434/v1')),
    )


def get_model_settings() -> dict:
    """Deterministic sampling for every pipeline stage. Bedrock has no seed parameter, so only Ollama gets one."""
    settings = {'temperature': 0}
    if os.getenv('LLM_PROVIDER', 'ollama').lower() != 'bedrock':
        settings['seed'] = int(os.getenv('LLM_SEED', '42'))
    return settings


def make_agent(output_type):
    """Build a pipeline agent: deterministic settings, and output-validation retries so a response
    that is missing required fields is re-requested instead of failing or being silently defaulted."""
    from pydantic_ai import Agent
    from pydantic_ai.output import NativeOutput

    return Agent(
        get_llm_model(),
        output_type=NativeOutput(output_type),
        model_settings=get_model_settings(),
        retries=int(os.getenv('LLM_RETRIES', '3')),
    )
