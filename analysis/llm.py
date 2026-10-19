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
