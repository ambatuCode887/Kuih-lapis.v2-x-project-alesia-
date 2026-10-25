"""Retry a failed primary ADK model request with a configured backup model."""

from __future__ import annotations

import logging
from typing import AsyncGenerator

from google.adk.models import LlmCapabilities
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse

logger = logging.getLogger(__name__)

FAILOVER_EXHAUSTED_MARKER = "LLM_FAILOVER_EXHAUSTED"


class LlmFailoverExhaustedError(RuntimeError):
    """Raised when both configured chat models fail before returning output."""


class FailoverLlm(BaseLlm):
    """Use the backup model when the primary fails before producing output."""

    primary_model: BaseLlm
    fallback_model: BaseLlm

    @property
    def capabilities(self) -> LlmCapabilities:
        primary = self.primary_model.capabilities
        fallback = self.fallback_model.capabilities
        return LlmCapabilities(
            output_schema_and_tools=(
                primary.output_schema_and_tools and fallback.output_schema_and_tools
            )
        )

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        primary_request = llm_request.model_copy(
            deep=True, update={"model": self.primary_model.model}
        )
        response_started = False
        primary_error: Exception | None = None

        try:
            async for response in self.primary_model.generate_content_async(
                primary_request, stream=stream
            ):
                response_started = True
                yield response
        except Exception as error:
            if response_started:
                raise
            primary_error = error

        if not response_started and primary_error is None:
            primary_error = RuntimeError("Primary LLM returned no response")
        if primary_error is None:
            return

        logger.warning(
            "Primary LLM %s failed before returning a response (%s); trying fallback %s",
            self.primary_model.model,
            type(primary_error).__name__,
            self.fallback_model.model,
        )
        fallback_request = llm_request.model_copy(
            deep=True, update={"model": self.fallback_model.model}
        )
        fallback_response_started = False
        try:
            async for response in self.fallback_model.generate_content_async(
                fallback_request, stream=stream
            ):
                fallback_response_started = True
                yield response
        except Exception as fallback_error:
            if fallback_response_started:
                raise
            logger.exception(
                "Fallback LLM %s also failed; both configured models are unavailable",
                self.fallback_model.model,
            )
            raise LlmFailoverExhaustedError(
                f"{FAILOVER_EXHAUSTED_MARKER}: primary and fallback models failed."
            ) from fallback_error
        if not fallback_response_started:
            raise LlmFailoverExhaustedError(
                f"{FAILOVER_EXHAUSTED_MARKER}: fallback returned no response."
            )
