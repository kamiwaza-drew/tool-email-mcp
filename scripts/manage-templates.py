#!/usr/bin/env python3
"""Manage Kamiwaza templates - list, import, sync, and push templates."""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import requests
import urllib3

try:
    from kamiwaza_sdk import KamiwazaClient as kz
    from kamiwaza_sdk.authentication import UserPasswordAuthenticator
except ImportError:  # Fallback for older client package name
    from kamiwaza_client import KamiwazaClient as kz
    from kamiwaza_client.authentication import UserPasswordAuthenticator

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

REPO_ROOT = Path(__file__).resolve().parents[1]
BUILD_DIR = REPO_ROOT / "build"


def _get_garden_dir_name(repo_version: str) -> str:
    """Map REPO_VERSION to directory name: v1 → 'default', v2 → 'v2'."""
    return "default" if repo_version == "v1" else "v2"


def _get_registry_root(repo_version: str | None = None) -> tuple[Path, str]:
    """Get the registry root path for the specified repo version.

    If repo_version is None, auto-detect by checking v2 first, then default (v1).
    Returns tuple of (path, detected_repo_version).
    """
    base = BUILD_DIR / "kamiwaza-extension-registry" / "garden"

    if repo_version:
        dir_name = _get_garden_dir_name(repo_version)
        return base / dir_name, repo_version

    # Auto-detect: check v2 first (new default), then default (v1/legacy)
    v2_path = base / "v2"
    if (v2_path / "apps.json").exists():
        return v2_path, "v2"

    default_path = base / "default"
    if (default_path / "apps.json").exists():
        return default_path, "v1"

    # Fallback to v2 (the new default)
    return v2_path, "v2"


def _get_apps_registry_file(repo_version: str | None = None) -> Path:
    """Get the apps.json file path for the specified repo version."""
    registry_root, _ = _get_registry_root(repo_version)
    return registry_root / "apps.json"


# Default paths (auto-detected)
REGISTRY_ROOT, _DETECTED_VERSION = _get_registry_root()
APPS_REGISTRY_FILE = REGISTRY_ROOT / "apps.json"
LEGACY_APPS_REGISTRY_FILE = BUILD_DIR / "kamiwaza-extension-registry" / "garden" / "default" / "apps.json"


def _normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


def _normalize_template_type_value(value: Any) -> str | None:
    if value is None:
        return None
    raw_value = getattr(value, "value", value)
    if isinstance(raw_value, str):
        cleaned = raw_value.strip().lower()
        if cleaned in {"apps", "tools", "services"}:
            cleaned = cleaned[:-1]
        if cleaned in {"app", "tool", "service"}:
            return cleaned
    return None


def _resolve_template_type(name: str | None, template_type: Any) -> str:
    resolved = _normalize_template_type_value(template_type)
    if resolved:
        return resolved
    if isinstance(name, str):
        lowered = name.lower()
        if lowered.startswith(("tool-", "mcp-")):
            return "tool"
        if lowered.startswith("service-"):
            return "service"
    return "app"


def _get_template_field(template: Any, field: str, default: Any = None) -> Any:
    if hasattr(template, field):
        return getattr(template, field)
    if isinstance(template, dict):
        return template.get(field, default)
    return default


def _filter_templates(templates: list[Any], desired_type: str) -> list[Any]:
    filtered = []
    for tpl in templates:
        name = _get_template_field(tpl, "name")
        template_type = _get_template_field(tpl, "template_type")
        if _resolve_template_type(name, template_type) == desired_type:
            filtered.append(tpl)
    return filtered


def _load_metadata(app_path: Path) -> dict[str, Any]:
    metadata_path = app_path / "kamiwaza.json"
    if not metadata_path.exists():
        raise FileNotFoundError(f"No kamiwaza.json found at {metadata_path}")

    with metadata_path.open() as f:
        return json.load(f)


def _load_registry_app_entry(app_name: str, template_name: str | None) -> dict[str, Any]:
    paths_to_check = [APPS_REGISTRY_FILE, LEGACY_APPS_REGISTRY_FILE]
    last_path = None
    found_any_path = False

    for registry_path in paths_to_check:
        if not registry_path.exists():
            continue

        found_any_path = True
        last_path = registry_path

        with registry_path.open() as f:
            apps_registry = json.load(f)

        candidates = []
        for entry in apps_registry:
            entry_name = entry.get("name")
            if entry_name == template_name or entry_name == app_name:
                candidates.append(entry)

        if not candidates:
            continue

        if len(candidates) > 1:
            print(f"Warning: Multiple registry entries matched '{template_name or app_name}'. Using first match.")

        if registry_path == LEGACY_APPS_REGISTRY_FILE:
            print(
                "Warning: Using legacy registry path. Run 'make build-registry' to "
                "generate the v2 registry at build/kamiwaza-extension-registry/garden/v2/."
            )

        return candidates[0]

    if not found_any_path:
        raise FileNotFoundError("Registry apps.json not found. Run 'make build-registry' before pushing.")

    raise ValueError(f"Template '{template_name or app_name}' not found in {last_path}. Run 'make build-registry'.")


def _get_tools_registry_file(repo_version: str | None = None) -> Path:
    """Get the tools.json file path for the specified repo version."""
    registry_root, _ = _get_registry_root(repo_version)
    return registry_root / "tools.json"


# Default tools paths (auto-detected)
TOOLS_REGISTRY_FILE = REGISTRY_ROOT / "tools.json"
LEGACY_TOOLS_REGISTRY_FILE = BUILD_DIR / "kamiwaza-extension-registry" / "garden" / "default" / "tools.json"


def _load_registry_tool_entry(tool_name: str, template_name: str | None) -> dict[str, Any]:
    """Load a tool entry from the registry (tools.json)."""
    paths_to_check = [TOOLS_REGISTRY_FILE, LEGACY_TOOLS_REGISTRY_FILE]
    last_path = None
    found_any_path = False

    for registry_path in paths_to_check:
        if not registry_path.exists():
            continue

        found_any_path = True
        last_path = registry_path

        with registry_path.open() as f:
            tools_registry = json.load(f)

        candidates = []
        for entry in tools_registry:
            entry_name = entry.get("name")
            if entry_name == template_name or entry_name == tool_name:
                candidates.append(entry)

        if not candidates:
            continue

        if len(candidates) > 1:
            print(f"Warning: Multiple registry entries matched '{template_name or tool_name}'. Using first match.")

        if registry_path == LEGACY_TOOLS_REGISTRY_FILE:
            print(
                "Warning: Using legacy registry path. Run 'make build-registry' to "
                "generate the v2 registry at build/kamiwaza-extension-registry/garden/v2/."
            )

        return candidates[0]

    if not found_any_path:
        raise FileNotFoundError("Registry tools.json not found. Run 'make build-registry' before pushing.")

    raise ValueError(
        f"Tool template '{template_name or tool_name}' not found in {last_path}. Run 'make build-registry'."
    )


def _clean_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in payload.items() if v is not None}


def _create_authenticated_session(
    base_url: str, username: str | None, password: str | None, skip_auth: bool = False
) -> tuple[requests.Session, bool]:
    """Create a session, optionally with authentication.

    Returns:
        tuple of (session, is_authenticated)
    """
    session = requests.Session()
    session.verify = False

    if skip_auth or not username or not password:
        return session, False

    login_url = f"{_normalize_base_url(base_url)}/auth/local-login"
    try:
        response = session.post(login_url, params={"username": username, "password": password})
        if response.status_code == 404:
            # Auth endpoint doesn't exist - system has auth disabled
            print("ℹ️  Auth endpoint not found - proceeding without authentication")
            return session, False
        elif response.status_code >= 400:
            print(f"⚠️  Login failed ({response.status_code}): {response.text.strip() or 'Unknown error'}")
            print("   Attempting to proceed without authentication...")
            return requests.Session(), False
        return session, True
    except requests.RequestException as exc:
        print(f"⚠️  Auth request failed: {exc}")
        print("   Attempting to proceed without authentication...")
        return requests.Session(), False


def _find_app_template(session: requests.Session, base_url: str, name: str) -> dict[str, Any] | None:
    """Find an existing app template by name.

    Returns:
        Template dict if found, None if not found.
        Raises RuntimeError on auth failure.
    """
    templates_url = f"{_normalize_base_url(base_url)}/apps/app_templates"
    response = session.get(templates_url)

    if response.status_code == 401:
        raise RuntimeError("Authentication required to access templates API")
    elif response.status_code == 403:
        raise RuntimeError("Permission denied to access templates API")

    response.raise_for_status()
    for template in response.json():
        if template.get("name") == name:
            return template
    return None


def garden_push_app_template(
    base_url: str,
    username: str | None,
    password: str | None,
    app_name: str,
    override_template_id: str | None = None,
    skip_auth: bool = False,
    extension_dir: str = "apps",
    default_template_type: str | None = None,
) -> None:
    extension_path = REPO_ROOT / extension_dir / app_name
    extension_label = extension_dir.rstrip("s").capitalize()

    if not extension_path.exists():
        print(f"❌ Error: {extension_label} '{app_name}' not found at {extension_path}")
        sys.exit(1)

    try:
        metadata = _load_metadata(extension_path)
    except Exception as exc:
        print(f"❌ Error loading metadata: {exc}")
        sys.exit(1)

    template_name = metadata.get("name") or app_name

    try:
        registry_entry = _load_registry_app_entry(app_name, template_name)
    except Exception as exc:
        print(f"❌ {exc}")
        sys.exit(1)

    # Get compose content directly from registry entry
    compose_content = registry_entry.get("compose_yml")
    if not compose_content or not compose_content.strip():
        print(f"❌ Registry entry for '{template_name}' is missing compose_yml. Run 'make build-registry'.")
        sys.exit(1)

    payload = dict(registry_entry)
    payload.pop("id", None)
    for transient_key in ("owner_id", "created_at", "updated_at"):
        payload.pop(transient_key, None)
    payload["compose_yml"] = compose_content
    payload = _clean_payload(payload)
    if default_template_type and not payload.get("template_type"):
        payload["template_type"] = default_template_type

    # Use SDK client for proper Keycloak authentication
    try:
        if skip_auth:
            client = get_client(base_url)
            is_authenticated = False
        else:
            client = get_client(base_url, username, password)
            is_authenticated = bool(username and password)
    except Exception as exc:
        print(f"❌ Failed to connect to Kamiwaza: {exc}")
        sys.exit(1)

    # Use SDK's HTTP client which has proper auth headers
    try:
        templates = client.apps.list_templates()
        existing = None
        if override_template_id:
            print(f"Using provided template_id {override_template_id} for update")
            existing = next((t for t in templates if str(t.id) == override_template_id), None)
            if not existing:
                existing = type("obj", (object,), {"id": override_template_id})()
        else:
            existing = next((t for t in templates if t.name == template_name), None)
    except Exception as exc:
        error_msg = str(exc)
        if "401" in error_msg or "Unauthorized" in error_msg:
            print("❌ Authentication required to access templates API")
            if skip_auth:
                print("   The target system requires authentication.")
                print("   Remove --no-auth and set KAMIWAZA_USERNAME/KAMIWAZA_PASSWORD.")
            else:
                print("   Verify KAMIWAZA_USERNAME and KAMIWAZA_PASSWORD are correct.")
            sys.exit(1)
        print(f"❌ Failed to list templates: {exc}")
        sys.exit(1)

    # Use SDK's authenticated session for create/update
    _normalize_base_url(base_url)

    try:
        if existing:
            action = "update"
            template_id = existing.id if hasattr(existing, "id") else existing.get("id")
            endpoint = f"apps/app_templates/{template_id}"
            result = client.put(endpoint, json=payload)
        else:
            action = "create"
            endpoint = "apps/app_templates"
            result = client.post(endpoint, json=payload)

        # SDK returns parsed JSON directly, raises on error
        version = (
            result.get("version", payload.get("version", "unknown"))
            if isinstance(result, dict)
            else payload.get("version", "unknown")
        )
        auth_status = " (authenticated)" if is_authenticated else " (no auth)"
        past_tense = "updated" if action == "update" else "created"
        print(f"✅ Successfully {past_tense} template '{template_name}' (version {version}){auth_status}")
    except Exception as exc:
        error_msg = str(exc)
        if "401" in error_msg or "Unauthorized" in error_msg:
            print(f"❌ Authentication required to {action} template.")
            print("   Set KAMIWAZA_USERNAME and KAMIWAZA_PASSWORD environment variables.")
        else:
            print(f"❌ Failed to {action} template '{template_name}': {exc}")
        sys.exit(1)


def garden_push_tool_template(
    base_url: str,
    username: str | None,
    password: str | None,
    tool_name: str,
    override_template_id: str | None = None,
    skip_auth: bool = False,
) -> None:
    """Push a tool template to a Kamiwaza instance."""
    tool_path = REPO_ROOT / "tools" / tool_name

    if not tool_path.exists():
        print(f"❌ Error: Tool '{tool_name}' not found at {tool_path}")
        sys.exit(1)

    try:
        metadata = _load_metadata(tool_path)
    except Exception as exc:
        print(f"❌ Error loading metadata: {exc}")
        sys.exit(1)

    template_name = metadata.get("name") or tool_name

    try:
        registry_entry = _load_registry_tool_entry(tool_name, template_name)
    except Exception as exc:
        print(f"❌ {exc}")
        sys.exit(1)

    # Build payload from registry entry
    payload = dict(registry_entry)
    payload.pop("id", None)
    for transient_key in ("owner_id", "created_at", "updated_at", "template_id"):
        payload.pop(transient_key, None)

    # Ensure required fields have defaults
    if "capabilities" not in payload:
        payload["capabilities"] = []
    if "required_env_vars" not in payload:
        payload["required_env_vars"] = []
    if "env_defaults" not in payload:
        payload["env_defaults"] = {}
    if "tags" not in payload:
        payload["tags"] = []
    if "verified" not in payload:
        payload["verified"] = False
    if "risk_tier" not in payload:
        payload["risk_tier"] = 1

    payload = _clean_payload(payload)

    # Use SDK client for proper authentication
    try:
        if skip_auth:
            client = get_client(base_url)
            is_authenticated = False
        else:
            client = get_client(base_url, username, password)
            is_authenticated = bool(username and password)
    except Exception as exc:
        print(f"❌ Failed to connect to Kamiwaza: {exc}")
        sys.exit(1)

    # Check if template already exists
    try:
        templates = client.tools.list_imported_templates()
        existing = None
        if override_template_id:
            print(f"Using provided template_id {override_template_id} for update")
            existing = next((t for t in templates if str(t.id) == override_template_id), None)
            if not existing:
                existing = type("obj", (object,), {"id": override_template_id})()
        else:
            existing = next((t for t in templates if t.name == template_name), None)
    except Exception as exc:
        error_msg = str(exc)
        if "401" in error_msg or "Unauthorized" in error_msg:
            print("❌ Authentication required to access templates API")
            if skip_auth:
                print("   The target system requires authentication.")
                print("   Remove --no-auth and set KAMIWAZA_USERNAME/KAMIWAZA_PASSWORD.")
            else:
                print("   Verify KAMIWAZA_USERNAME and KAMIWAZA_PASSWORD are correct.")
            sys.exit(1)
        print(f"❌ Failed to list templates: {exc}")
        sys.exit(1)

    # Create or update tool template
    # Note: Tool templates use the same AppTemplate model as apps.
    # CREATE uses apps/app_templates (no separate tool create endpoint exists).
    # UPDATE uses tool/tool_templates/{id} for tool-specific operations.
    try:
        if existing:
            action = "update"
            template_id = existing.id if hasattr(existing, "id") else existing.get("id")
            endpoint = f"tool/tool_templates/{template_id}"
            result = client.put(endpoint, json=payload)
        else:
            action = "create"
            endpoint = "apps/app_templates"
            result = client.post(endpoint, json=payload)

        version = (
            result.get("version", payload.get("version", "unknown"))
            if isinstance(result, dict)
            else payload.get("version", "unknown")
        )
        auth_status = " (authenticated)" if is_authenticated else " (no auth)"
        past_tense = "updated" if action == "update" else "created"
        print(f"✅ Successfully {past_tense} tool template '{template_name}' (version {version}){auth_status}")
    except Exception as exc:
        error_msg = str(exc)
        if "401" in error_msg or "Unauthorized" in error_msg:
            print(f"❌ Authentication required to {action} template.")
            print("   Set KAMIWAZA_USERNAME and KAMIWAZA_PASSWORD environment variables.")
        else:
            print(f"❌ Failed to {action} tool template '{template_name}': {exc}")
        sys.exit(1)


def garden_sync_templates(
    base_url: str,
    username: str | None,
    password: str | None,
    names: list[str] | None = None,
    remote_base_url: str | None = None,
    remote_apps_path: str | None = None,
    remote_tools_path: str | None = None,
    skip_auth: bool = False,
) -> None:
    _session, _ = _create_authenticated_session(base_url, username, password, skip_auth)


def garden_list_templates(
    base_url: str,
    username: str | None,
    password: str | None,
    output_format: str = "table",
    skip_auth: bool = False,
) -> None:
    # Use SDK client for proper authentication
    try:
        if skip_auth:
            client = get_client(base_url)
        else:
            client = get_client(base_url, username, password)
    except Exception as exc:
        print(f"❌ Failed to connect to Kamiwaza: {exc}")
        sys.exit(1)

    try:
        templates = client.apps.list_templates()
    except Exception as exc:
        print(f"❌ Failed to list templates: {exc}")
        sys.exit(1)

    if output_format == "json":
        print(json.dumps([t.model_dump() for t in templates], indent=2, default=str))
        return

    if not templates:
        print("No templates found.")
        return

    print("\n📋 Installed Templates:")
    print(f"{'Name':<40} {'Type':<10} {'Version':<12} ID")
    print("-" * 100)
    for tpl in templates:
        name = tpl.name if hasattr(tpl, "name") else tpl.get("name", "unknown")
        version = tpl.version if hasattr(tpl, "version") else tpl.get("version", "n/a")
        tpl_id = str(tpl.id) if hasattr(tpl, "id") else tpl.get("id", "n/a")
        template_type = _resolve_template_type(name, getattr(tpl, "template_type", None))
        print(f"{name:<40} {template_type:<10} {version:<12} {tpl_id}")


def get_client(base_url: str, username: str | None = None, password: str | None = None) -> kz:
    """Initialize Kamiwaza client with optional authentication.

    Note: Set KAMIWAZA_VERIFY_SSL=false to disable SSL verification for self-signed certs.
    """
    # Initialize client without auth first
    client = kz(base_url=base_url)

    # Add authentication if credentials provided
    if username and password:
        authenticator = UserPasswordAuthenticator(username=username, password=password, auth_service=client.auth)
        client = kz(base_url=base_url, authenticator=authenticator)

    return client


def list_app_templates(client: kz, output_format: str = "table") -> None:
    """List available app templates."""
    try:
        templates = _filter_templates(client.apps.list_templates(), "app")

        if output_format == "json":
            print(json.dumps([t.model_dump() for t in templates], indent=2, default=str))
        else:
            print(f"\n📋 Available App Templates ({len(templates)} total):\n")
            print(f"{'Name':<30} {'Version':<10} {'Risk':<6} {'Verified':<10} Description")
            print("-" * 90)
            for t in templates:
                name = t.name[:29] + "…" if len(t.name) > 30 else t.name
                desc = t.description[:40] + "…" if t.description and len(t.description) > 40 else (t.description or "")
                print(f"{name:<30} {t.version or '1.0.0':<10} {t.risk_tier:<6} {'✓' if t.verified else '✗':<10} {desc}")
    except Exception as e:
        print(f"❌ Error listing app templates: {e}", file=sys.stderr)
        sys.exit(1)


def list_service_templates(client: kz, output_format: str = "table") -> None:
    """List available service templates."""
    try:
        templates = _filter_templates(client.apps.list_templates(), "service")

        if output_format == "json":
            print(json.dumps([t.model_dump() for t in templates], indent=2, default=str))
        else:
            print(f"\n🧰 Available Service Templates ({len(templates)} total):\n")
            print(f"{'Name':<30} {'Version':<10} {'Risk':<6} {'Verified':<10} Description")
            print("-" * 90)
            for t in templates:
                name = t.name[:29] + "…" if len(t.name) > 30 else t.name
                desc = t.description[:40] + "…" if t.description and len(t.description) > 40 else (t.description or "")
                print(f"{name:<30} {t.version or '1.0.0':<10} {t.risk_tier:<6} {'✓' if t.verified else '✗':<10} {desc}")
    except Exception as e:
        print(f"❌ Error listing service templates: {e}", file=sys.stderr)
        sys.exit(1)


def list_tool_templates(client: kz, output_format: str = "table") -> None:
    """List available tool templates."""
    try:
        templates = client.tools.list_available_templates()

        if output_format == "json":
            print(json.dumps([t.model_dump() for t in templates], indent=2, default=str))
        else:
            print(f"\n🔧 Available Tool Templates ({len(templates)} total):\n")
            print(f"{'Name':<30} {'Image':<40} {'Env Vars'}")
            print("-" * 90)
            for t in templates:
                name = t.name[:29] + "…" if len(t.name) > 30 else t.name
                image = t.image[:39] + "…" if len(t.image) > 40 else t.image
                env_vars = ", ".join(t.required_env_vars) if t.required_env_vars else "None"
                print(f"{name:<30} {image:<40} {env_vars}")
    except Exception as e:
        print(f"❌ Error listing tool templates: {e}", file=sys.stderr)
        sys.exit(1)


def _resolve_deployment_type(name: str | None) -> str:
    if isinstance(name, str) and name.lower().startswith("service-"):
        return "service"
    return "app"


def list_deployments(client: kz, deployment_type: str = "all", output_format: str = "table") -> None:
    """List current deployments."""
    deployments = []

    if deployment_type in ["all", "apps", "services"]:
        try:
            app_deployments = client.apps.list_deployments()
            for deployment in app_deployments:
                dtype = _resolve_deployment_type(getattr(deployment, "name", None))
                if deployment_type == "apps" and dtype != "app":
                    continue
                if deployment_type == "services" and dtype != "service":
                    continue
                deployments.append((dtype, deployment))
        except Exception as e:
            print(f"⚠️  Warning: Could not list app deployments: {e}", file=sys.stderr)

    if deployment_type in ["all", "tools"]:
        try:
            tool_deployments = client.tools.list_deployments()
            deployments.extend([("tool", d) for d in tool_deployments])
        except Exception as e:
            print(f"⚠️  Warning: Could not list tool deployments: {e}", file=sys.stderr)

    if output_format == "json":
        output = {
            "apps": [d[1].model_dump() for d in deployments if d[0] == "app"],
            "services": [d[1].model_dump() for d in deployments if d[0] == "service"],
            "tools": [d[1].model_dump() for d in deployments if d[0] == "tool"],
        }
        print(json.dumps(output, indent=2, default=str))
    else:
        print(f"\n🚀 Current Deployments ({len(deployments)} total):\n")
        if not deployments:
            print("No deployments found.")
        else:
            print(f"{'Type':<6} {'Name':<30} {'Status':<12} {'ID'}")
            print("-" * 80)
            for dtype, d in deployments:
                name = d.name[:29] + "…" if len(d.name) > 30 else d.name
                print(f"{dtype:<6} {name:<30} {d.status:<12} {d.id}")


def inspect_template(client: kz, template_type: str, template_name: str) -> None:
    """Inspect a template's details from Kamiwaza."""
    try:
        if template_type in ["app", "service"]:
            templates = client.apps.list_templates()
            template = next(
                (
                    t
                    for t in templates
                    if t.name == template_name
                    and _resolve_template_type(t.name, getattr(t, "template_type", None)) == template_type
                ),
                None,
            )
        else:
            templates = client.tools.list_imported_templates()
            template = next((t for t in templates if t.name == template_name), None)

        if not template:
            print(f"❌ Error: Template '{template_name}' not found")
            sys.exit(1)

        print(f"\n📋 Template Details: {template_name}\n")
        print(f"{'=' * 60}")
        print(f"Type:        {template_type}")
        print(f"Name:        {template.name}")
        print(f"Version:     {template.version}")
        print(f"Risk Tier:   {template.risk_tier}")
        print(f"Verified:    {'✅' if template.verified else '❌'}")
        if hasattr(template, "description") and template.description:
            print(f"Description: {template.description}")
        if hasattr(template, "source_type"):
            print(f"Source Type: {template.source_type}")
        if hasattr(template, "visibility"):
            print(f"Visibility:  {template.visibility}")
        print(f"{'=' * 60}\n")

        # Show full JSON if requested
        print("Full template data (JSON):")
        print(json.dumps(template.model_dump(), indent=2, default=str))

    except Exception as e:
        print(f"❌ Error inspecting template: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Manage Kamiwaza templates")
    parser.add_argument(
        "--base-url",
        default=os.getenv("KAMIWAZA_API_URL", "https://localhost/api"),
        help=("Kamiwaza API base URL (default: $KAMIWAZA_API_URL or https://localhost/api)"),
    )
    parser.add_argument(
        "--sync-base-url",
        default=os.getenv("KAMIWAZA_REMOTE_TEMPLATE_BASE_URL", "https://localhost:44443"),
        help=("Remote template base URL (default: $KAMIWAZA_REMOTE_TEMPLATE_BASE_URL or https://localhost:44443)"),
    )
    parser.add_argument(
        "--sync-apps-path",
        default=os.getenv("KAMIWAZA_REMOTE_TEMPLATE_APPS_PATH", "/apps.json"),
        help=("Remote template apps path (default: $KAMIWAZA_REMOTE_TEMPLATE_APPS_PATH or /apps.json)"),
    )
    parser.add_argument(
        "--sync-tools-path",
        default=os.getenv("KAMIWAZA_REMOTE_TEMPLATE_TOOLS_PATH", "/tools.json"),
        help=("Remote template tools path (default: $KAMIWAZA_REMOTE_TEMPLATE_TOOLS_PATH or /tools.json)"),
    )
    parser.add_argument(
        "--username",
        default=os.getenv("KAMIWAZA_USERNAME"),
        help="Username for authentication (default: $KAMIWAZA_USERNAME)",
    )
    parser.add_argument(
        "--password",
        default=os.getenv("KAMIWAZA_PASSWORD"),
        help="Password for authentication (default: $KAMIWAZA_PASSWORD)",
    )
    parser.add_argument(
        "--no-auth",
        action="store_true",
        help="Skip authentication (for public endpoints)",
    )
    parser.add_argument(
        "--format",
        choices=["table", "json"],
        default="table",
        help="Output format (default: table)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # List commands
    list_parser = subparsers.add_parser("list", help="List templates or deployments")
    list_parser.add_argument(
        "target",
        choices=["apps", "services", "tools", "all", "deployments"],
        help="What to list",
    )

    # Garden push commands
    garden_push_parser = subparsers.add_parser(
        "garden-push",
        help="Push a local app, service, or tool template to Kamiwaza Garden",
    )
    garden_push_parser.add_argument("type", choices=["app", "service", "tool"], help="Extension type")
    garden_push_parser.add_argument("name", help="Extension name")
    garden_push_parser.add_argument("--template-id", help="Optional template ID to force update")
    garden_push_parser.add_argument(
        "--no-auth",
        action="store_true",
        help="Skip authentication (for systems with KAMIWAZA_USE_AUTH=false)",
    )

    garden_list_parser = subparsers.add_parser("garden-list", help="List App Garden templates from Kamiwaza")
    garden_list_parser.add_argument(
        "--format",
        choices=["table", "json"],
        default="table",
        help="Output format (default: table)",
    )
    garden_list_parser.add_argument(
        "--no-auth",
        action="store_true",
        help="Skip authentication (for systems with KAMIWAZA_USE_AUTH=false)",
    )

    # Garden sync command
    garden_sync_parser = subparsers.add_parser("garden-sync", help="Sync remote Kamiwaza Garden templates")
    garden_sync_parser.add_argument(
        "names",
        nargs="*",
        help="Optional list of template names to sync (defaults to all)",
    )

    # Inspect command
    inspect_parser = subparsers.add_parser("inspect", help="Inspect template details")
    inspect_parser.add_argument("type", choices=["app", "service", "tool"], help="Template type")
    inspect_parser.add_argument("name", help="Template name")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Execute garden-specific commands before initializing the SDK client
    if args.command == "garden-push":
        if args.type == "app":
            garden_push_app_template(
                args.base_url,
                args.username,
                args.password,
                args.name,
                args.template_id,
                skip_auth=args.no_auth,
            )
        elif args.type == "service":
            garden_push_app_template(
                args.base_url,
                args.username,
                args.password,
                args.name,
                args.template_id,
                skip_auth=args.no_auth,
                extension_dir="services",
                default_template_type="service",
            )
        elif args.type == "tool":
            garden_push_tool_template(
                args.base_url,
                args.username,
                args.password,
                args.name,
                args.template_id,
                skip_auth=args.no_auth,
            )
        return

    if args.command == "garden-sync":
        sync_names = args.names if args.names else None
        skip_auth = getattr(args, "no_auth", False)
        garden_sync_templates(
            args.base_url,
            args.username,
            args.password,
            sync_names,
            args.sync_base_url,
            args.sync_apps_path,
            args.sync_tools_path,
            skip_auth=skip_auth,
        )
        return

    if args.command == "garden-list":
        skip_auth = getattr(args, "no_auth", False)
        garden_list_templates(
            args.base_url,
            args.username,
            args.password,
            args.format,
            skip_auth=skip_auth,
        )
        return

    # Initialize SDK client for remaining commands
    if args.no_auth:
        client = get_client(args.base_url)
    else:
        client = get_client(args.base_url, args.username, args.password)

    if args.command == "list":
        if args.target == "apps":
            list_app_templates(client, args.format)
        elif args.target == "services":
            list_service_templates(client, args.format)
        elif args.target == "tools":
            list_tool_templates(client, args.format)
        elif args.target == "all":
            list_app_templates(client, args.format)
            if args.format == "table":
                print()  # Add spacing between tables
            list_service_templates(client, args.format)
            if args.format == "table":
                print()
            list_tool_templates(client, args.format)
        elif args.target == "deployments":
            list_deployments(client, "all", args.format)

    elif args.command == "inspect":
        inspect_template(client, args.type, args.name)


if __name__ == "__main__":
    main()
