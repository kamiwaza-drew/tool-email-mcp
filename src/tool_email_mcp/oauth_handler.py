"""OAuth flow handler for multi-provider authentication.

Handles OAuth authorization and callback for Gmail and Outlook.
"""

import os
import aiohttp
from typing import Dict, Optional, Any
from urllib.parse import urlencode

from starlette.requests import Request
from starlette.responses import RedirectResponse, JSONResponse

from .providers_config import (
    get_provider_config,
    get_provider_client_id,
    get_provider_client_secret,
    get_provider_tenant_id,
    is_provider_configured
)
from .session_manager import SessionManager


class OAuthHandler:
    """Handles OAuth flow for email providers."""

    def __init__(self, session_manager: SessionManager):
        """Initialize OAuth handler.

        Args:
            session_manager: Session manager instance
        """
        self.session_manager = session_manager

    async def handle_authorize(self, request: Request) -> RedirectResponse | JSONResponse:
        """Initiate OAuth flow for specified provider.

        Query params:
            provider: "gmail" or "outlook"

        Returns:
            Redirect to provider's OAuth consent screen
        """
        provider_name = request.query_params.get("provider", "gmail")

        # Validate provider
        if not is_provider_configured(provider_name):
            return JSONResponse(
                {
                    "error": f"Provider '{provider_name}' not configured",
                    "hint": f"Set {provider_name.upper()}_CLIENT_ID environment variable"
                },
                status_code=400
            )

        provider_config = get_provider_config(provider_name)
        if not provider_config:
            return JSONResponse(
                {"error": f"Unknown provider: {provider_name}"},
                status_code=400
            )

        # Get OAuth credentials
        client_id = get_provider_client_id(provider_name)
        redirect_uri = os.getenv("OAUTH_REDIRECT_URI", "http://localhost:8000/oauth/callback")

        # Generate state token (CSRF protection)
        state = self.session_manager.create_oauth_state(provider_name)

        # Build provider-specific OAuth URL
        auth_url = provider_config.auth_url

        # Handle tenant ID for Outlook
        if provider_name == "outlook":
            tenant_id = get_provider_tenant_id(provider_name)
            auth_url = auth_url.format(tenant=tenant_id)

        # Build authorization URL
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(provider_config.scopes),
            "state": state,
            "access_type": "online",  # No refresh token (short-lived only)
            "prompt": "consent"  # Always show consent screen
        }

        oauth_url = f"{auth_url}?{urlencode(params)}"

        print(f"🔑 Initiating OAuth flow for {provider_name}...")

        return RedirectResponse(oauth_url, status_code=302)

    async def handle_callback(self, request: Request) -> RedirectResponse | JSONResponse:
        """Handle OAuth callback from provider.

        Query params:
            code: Authorization code
            state: State token (CSRF protection)
            error: Error message (if authorization failed)

        Returns:
            Redirect to success page or error response
        """
        code = request.query_params.get("code")
        state = request.query_params.get("state")
        error = request.query_params.get("error")

        # Handle errors from provider
        if error:
            print(f"❌ OAuth error: {error}")
            return RedirectResponse(
                f"/oauth/error?error={error}",
                status_code=302
            )

        if not code or not state:
            return JSONResponse(
                {"error": "Missing code or state parameter"},
                status_code=400
            )

        # Verify state (CSRF protection)
        provider_name = self.session_manager.verify_oauth_state(state)
        if not provider_name:
            return JSONResponse(
                {"error": "Invalid or expired state token"},
                status_code=400
            )

        print(f"✅ State verified for {provider_name}")

        # Exchange authorization code for access token
        try:
            token_data = await self._exchange_code_for_token(
                provider_name, code
            )
        except Exception as e:
            print(f"❌ Token exchange failed: {e}")
            return JSONResponse(
                {"error": f"Token exchange failed: {str(e)}"},
                status_code=500
            )

        access_token = token_data.get("access_token")
        if not access_token:
            return JSONResponse(
                {"error": "No access token in response"},
                status_code=500
            )

        # Get user email
        try:
            user_email = await self._get_user_email(provider_name, access_token)
        except Exception as e:
            print(f"⚠️  Could not fetch user email: {e}")
            user_email = "unknown@example.com"

        # Create session
        session_id = self.session_manager.create_session(
            provider=provider_name,
            access_token=access_token,
            user_email=user_email
        )

        # Set session cookie and redirect
        response = RedirectResponse("/oauth/success", status_code=302)
        response.set_cookie(
            "email_session",
            session_id,
            max_age=int(os.getenv("SESSION_TIMEOUT", "3600")),
            httponly=True,
            secure=os.getenv("COOKIE_SECURE", "true").lower() == "true",
            samesite=os.getenv("COOKIE_SAMESITE", "lax")
        )

        print(f"🎉 OAuth successful: {user_email} ({provider_name})")

        return response

    async def _exchange_code_for_token(
        self,
        provider_name: str,
        code: str
    ) -> Dict[str, Any]:
        """Exchange authorization code for access token.

        Args:
            provider_name: Provider name
            code: Authorization code

        Returns:
            Token response dict

        Raises:
            Exception: If token exchange fails
        """
        provider_config = get_provider_config(provider_name)
        if not provider_config:
            raise ValueError(f"Unknown provider: {provider_name}")

        # Get OAuth credentials
        client_id = get_provider_client_id(provider_name)
        client_secret = get_provider_client_secret(provider_name)
        redirect_uri = os.getenv("OAUTH_REDIRECT_URI", "http://localhost:8000/oauth/callback")

        # Build token URL
        token_url = provider_config.token_url
        if provider_name == "outlook":
            tenant_id = get_provider_tenant_id(provider_name)
            token_url = token_url.format(tenant=tenant_id)

        # Exchange code for token
        async with aiohttp.ClientSession() as session:
            async with session.post(
                token_url,
                data={
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code"
                }
            ) as resp:
                if resp.status != 200:
                    error_data = await resp.text()
                    raise Exception(f"Token exchange failed ({resp.status}): {error_data}")

                return await resp.json()

    async def _get_user_email(self, provider_name: str, access_token: str) -> str:
        """Get user's email from provider API.

        Args:
            provider_name: Provider name
            access_token: OAuth access token

        Returns:
            User's email address

        Raises:
            Exception: If userinfo request fails
        """
        provider_config = get_provider_config(provider_name)
        if not provider_config:
            raise ValueError(f"Unknown provider: {provider_name}")

        userinfo_url = provider_config.userinfo_url

        async with aiohttp.ClientSession() as session:
            async with session.get(
                userinfo_url,
                headers={"Authorization": f"Bearer {access_token}"}
            ) as resp:
                if resp.status != 200:
                    error_data = await resp.text()
                    raise Exception(f"Userinfo request failed ({resp.status}): {error_data}")

                data = await resp.json()

                # Provider-specific email extraction
                if provider_name == "gmail":
                    return data.get("email", "unknown@example.com")
                elif provider_name == "outlook":
                    return data.get("mail") or data.get("userPrincipalName", "unknown@example.com")

                return "unknown@example.com"
