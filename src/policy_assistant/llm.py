from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel

from .config import Settings


def create_chat_model(settings: Settings) -> BaseChatModel:
    """Create one LangChain chat model from the selected provider."""
    if settings.provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.model,
            api_key=settings.api_key,
            temperature=0,
            use_responses_api=True,
        )
    if settings.provider == "groq":
        from langchain_groq import ChatGroq

        return ChatGroq(
            model=settings.model,
            api_key=settings.api_key,
            temperature=0,
        )

    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(
        model=settings.model,
        google_api_key=settings.api_key,
        temperature=0,
    )
