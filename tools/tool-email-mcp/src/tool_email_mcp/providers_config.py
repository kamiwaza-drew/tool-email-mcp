"""OAuth provider configuration registry.

Defines supported email providers and their OAuth settings.
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class OAuthProvider:
    """OAuth provider configuration."""

    name: str
    auth_url: str
    token_url: str
    userinfo_url: str
    scopes: list[str]
    client_id_env: str
    client_secret_env: str
    tenant_id_env: Optional[str] = None
    logo: str = ""


# Provider registry
OAUTH_PROVIDERS: Dict[str, OAuthProvider] = {
    "gmail": OAuthProvider(
        name="Google / Gmail",
        auth_url="https://accounts.google.com/o/oauth2/v2/auth",
        token_url="https://oauth2.googleapis.com/token",
        userinfo_url="https://www.googleapis.com/oauth2/v2/userinfo",
        scopes=[
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/gmail.modify",
            "https://www.googleapis.com/auth/userinfo.email",
        ],
        client_id_env="OAUTH_GMAIL_CLIENT_ID",
        client_secret_env="OAUTH_GMAIL_CLIENT_SECRET",
        logo="/static/google-logo.svg"
    ),
    "outlook": OAuthProvider(
        name="Microsoft / Outlook",
        auth_url="https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize",
        token_url="https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
        userinfo_url="https://graph.microsoft.com/v1.0/me",
        scopes=[
            "https://graph.microsoft.com/Mail.Read",
            "https://graph.microsoft.com/Mail.ReadWrite",
            "https://graph.microsoft.com/Mail.Send",
            "https://graph.microsoft.com/User.Read",
        ],
        client_id_env="OAUTH_OUTLOOK_CLIENT_ID",
        client_secret_env="OAUTH_OUTLOOK_CLIENT_SECRET",
        tenant_id_env="OAUTH_OUTLOOK_TENANT_ID",
        logo="/static/microsoft-logo.svg"
    ),
}


def get_provider_config(provider_name: str) -> Optional[OAuthProvider]:
    """Get OAuth configuration for a provider.

    Args:
        provider_name: Provider identifier ("gmail" or "outlook")

    Returns:
        OAuthProvider config or None if not found
    """
    return OAUTH_PROVIDERS.get(provider_name)


def get_provider_client_id(provider_name: str) -> Optional[str]:
    """Get OAuth client ID for a provider from environment.

    Args:
        provider_name: Provider identifier

    Returns:
        Client ID or None if not configured
    """
    provider = get_provider_config(provider_name)
    if not provider:
        return None
    return os.getenv(provider.client_id_env)


def get_provider_client_secret(provider_name: str) -> Optional[str]:
    """Get OAuth client secret for a provider from environment.

    Args:
        provider_name: Provider identifier

    Returns:
        Client secret or None if not configured
    """
    provider = get_provider_config(provider_name)
    if not provider:
        return None
    return os.getenv(provider.client_secret_env)


def get_provider_tenant_id(provider_name: str) -> str:
    """Get tenant ID for Microsoft provider.

    Args:
        provider_name: Provider identifier

    Returns:
        Tenant ID or "common" for multi-tenant
    """
    provider = get_provider_config(provider_name)
    if not provider or not provider.tenant_id_env:
        return "common"
    return os.getenv(provider.tenant_id_env, "common")


def is_provider_configured(provider_name: str) -> bool:
    """Check if a provider is configured with OAuth credentials.

    Args:
        provider_name: Provider identifier

    Returns:
        True if provider has client ID configured
    """
    client_id = get_provider_client_id(provider_name)
    return client_id is not None and client_id != ""


def get_configured_providers() -> list[str]:
    """Get list of configured provider names.

    Returns:
        List of provider names that have OAuth credentials configured
    """
    return [
        name for name in OAUTH_PROVIDERS.keys()
        if is_provider_configured(name)
    ]


def get_provider_display_info() -> list[Dict[str, Any]]:
    """Get display information for all configured providers.

    Returns:
        List of provider info dicts for UI rendering
    """
    configured = get_configured_providers()
    return [
        {
            "id": name,
            "name": OAUTH_PROVIDERS[name].name,
            "logo": OAUTH_PROVIDERS[name].logo,
            "configured": True
        }
        for name in configured
    ]
