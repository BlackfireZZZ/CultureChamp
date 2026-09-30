"""Select the server-only model adapter from explicit operator settings."""

from app.core.config import Settings
from app.infrastructure.model.gateway import GroundedFakeProvider, ModelProvider
from app.infrastructure.model.http import HttpModelProvider


def configured_provider(settings: Settings) -> ModelProvider:
    if settings.model_provider == "fake":
        if settings.app_env != "development":
            raise ValueError("fake model provider is available only in development")
        return GroundedFakeProvider()
    if not settings.model_policy_approved:
        raise ValueError("external model policy is not approved")
    if not settings.model_api_endpoint or not settings.model_api_name or not settings.model_api_key:
        raise ValueError("external model configuration is incomplete")
    return HttpModelProvider(
        endpoint=settings.model_api_endpoint,
        model=settings.model_api_name,
        api_key=settings.model_api_key.get_secret_value(),
        policy_approved=True,
    )
