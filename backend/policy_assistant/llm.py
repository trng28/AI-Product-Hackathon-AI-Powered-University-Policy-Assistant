from __future__ import annotations

from typing import Any

from .config import Settings


class _OpenAIStructuredModel:
    def __init__(self, client: Any, model: str, schema: type) -> None:
        self.client = client
        self.model = model
        self.schema = schema

    def invoke(self, messages: list[Any]):
        instructions = "\n\n".join(
            str(message.content)
            for message in messages
            if getattr(message, "type", "") == "system"
        )
        user_input = "\n\n".join(
            str(message.content)
            for message in messages
            if getattr(message, "type", "") != "system"
        )
        response = self.client.responses.parse(
            model=self.model,
            instructions=instructions,
            input=user_input,
            text_format=self.schema,
            store=False,
        )
        if response.output_parsed is None:
            raise RuntimeError("OpenAI returned no structured output")
        return response.output_parsed


class DirectOpenAIChat:
    """Small structured-output adapter that avoids LangChain's Torch import."""

    def __init__(self, model: str, api_key: str) -> None:
        from openai import OpenAI

        self.client = OpenAI(api_key=api_key)
        self.model = model

    def with_structured_output(self, schema: type) -> _OpenAIStructuredModel:
        return _OpenAIStructuredModel(self.client, self.model, schema)


def create_chat_model(settings: Settings) -> Any:
    if settings.provider == "openai":
        return DirectOpenAIChat(settings.model, settings.api_key)
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
