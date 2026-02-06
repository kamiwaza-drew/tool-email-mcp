#!/usr/bin/env python3
"""
Kamiwaza App Garden Remote Deployer

Deploy converted apps directly to remote Kamiwaza instances (e.g., babynator2 cluster).

Usage:
    python deploy.py --app-path apps/my-app --url https://babynator2.example.com --password <pwd>
    python deploy.py --app-path apps/my-app --cluster babynator2  # Uses predefined cluster
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

try:
    import requests
    import urllib3
    import yaml
    urllib3.disable_warnings()
except ImportError:
    print("Missing dependencies. Install with: pip install requests pyyaml")
    sys.exit(1)


# Predefined cluster configurations
CLUSTERS = {
    "babynator2": {
        "url": "https://192.168.100.118",
        "username": "admin",
        "description": "Babynator2 development cluster"
    },
    # Add more clusters as needed
}


def log(msg: str, level: str = "INFO"):
    """Print a log message."""
    colors = {
        "INFO": "\033[94m",
        "SUCCESS": "\033[92m",
        "WARNING": "\033[93m",
        "ERROR": "\033[91m",
        "STEP": "\033[96m",
    }
    reset = "\033[0m"
    color = colors.get(level, "")
    print(f"{color}[{level}]{reset} {msg}")


def run_command(cmd: list, cwd: str | None = None, check: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            check=check,
            capture_output=True,
            text=True,
        )
        return result
    except subprocess.CalledProcessError as e:
        log(f"Command failed: {' '.join(cmd)}", "ERROR")
        log(f"stderr: {e.stderr}", "ERROR")
        raise


def authenticate(session: requests.Session, url: str, username: str, password: str) -> str:
    """Authenticate to Kamiwaza and return access token."""
    log(f"Authenticating to {url}...")

    auth_response = session.post(
        f"{url}/api/auth/token",
        data={
            "grant_type": "password",
            "username": username,
            "password": password,
            "scope": "openid email profile",
            "client_id": "kamiwaza-platform",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    if auth_response.status_code != 200:
        log(f"Authentication failed: {auth_response.status_code}", "ERROR")
        log(f"Response: {auth_response.text}", "ERROR")
        raise RuntimeError("Authentication failed")

    token = auth_response.json()["access_token"]
    log("Authenticated successfully", "SUCCESS")
    return token


def build_and_push_images(app_path: Path, version: str, skip_build: bool = False):
    """Build and push multi-arch Docker images to Docker Hub."""
    if skip_build:
        log("Skipping Docker build (--skip-build)", "WARNING")
        return

    log("Building and pushing Docker images (multi-arch)...", "STEP")

    # Read compose to find services
    compose_path = app_path / "docker-compose.yml"
    if not compose_path.exists():
        compose_path = app_path / "docker-compose.yaml"

    if not compose_path.exists():
        log("No docker-compose.yml found, skipping build", "WARNING")
        return

    with open(compose_path) as f:
        compose_data = yaml.safe_load(f)

    # Find kamiwaza.json to get app name
    kamiwaza_json = app_path / "kamiwaza.json"
    if kamiwaza_json.exists():
        with open(kamiwaza_json) as f:
            metadata = json.load(f)
        app_name = metadata.get("name", app_path.name).lower().replace(" ", "-")
    else:
        app_name = app_path.name

    # Build each service
    services = compose_data.get("services", {})
    for service_name, service_config in services.items():
        build_config = service_config.get("build")
        if not build_config:
            continue

        # Determine image tag
        image = service_config.get("image", f"kamiwazaai/{app_name}-{service_name}:v{version}")

        # Determine Dockerfile path
        if isinstance(build_config, dict):
            dockerfile = build_config.get("dockerfile", "Dockerfile")
            context = build_config.get("context", ".")
        else:
            dockerfile = "Dockerfile"
            context = build_config

        # Resolve paths
        dockerfile_path = app_path / dockerfile
        if not dockerfile_path.exists():
            dockerfile_path = app_path / service_name / "Dockerfile"

        context_path = app_path / context
        if service_name in ["frontend", "backend"] and (app_path / service_name).exists():
            context_path = app_path / service_name
            dockerfile_path = context_path / "Dockerfile"

        if not dockerfile_path.exists():
            log(f"Dockerfile not found for {service_name}, skipping", "WARNING")
            continue

        log(f"Building {service_name}: {image}")

        # Build with buildx for multi-arch
        cmd = [
            "docker", "buildx", "build",
            "--platform", "linux/amd64,linux/arm64",
            "-t", image,
            "--push",
            "-f", str(dockerfile_path),
            str(context_path)
        ]

        try:
            result = run_command(cmd, check=False)
            if result.returncode == 0:
                log(f"Built and pushed {image}", "SUCCESS")
            else:
                log(f"Build failed for {service_name}: {result.stderr}", "ERROR")
                raise RuntimeError(f"Docker build failed for {service_name}")
        except Exception as e:
            log(f"Build error: {e}", "ERROR")
            raise


def sync_compose(project_root: Path):
    """Run make sync-compose to generate appgarden compose."""
    log("Syncing docker-compose files...", "STEP")

    makefile = project_root / "Makefile"
    if makefile.exists():
        try:
            result = run_command(["make", "sync-compose"], cwd=str(project_root), check=False)
            if result.returncode == 0:
                log("Compose files synced", "SUCCESS")
            else:
                log("sync-compose had issues, continuing...", "WARNING")
        except Exception:
            log("make sync-compose not available, skipping", "WARNING")
    else:
        log("No Makefile found, skipping sync-compose", "WARNING")


def deploy_template(
    session: requests.Session,
    url: str,
    token: str,
    app_path: Path,
) -> dict:
    """Deploy app template to remote Kamiwaza instance."""
    log("Deploying template to Kamiwaza...", "STEP")

    headers = {"Authorization": f"Bearer {token}"}

    # Load metadata from kamiwaza.json
    kamiwaza_json = app_path / "kamiwaza.json"
    if not kamiwaza_json.exists():
        raise FileNotFoundError(f"kamiwaza.json not found in {app_path}")

    with open(kamiwaza_json) as f:
        metadata = json.load(f)

    # Load compose YAML - prefer appgarden version
    compose_path = app_path / "docker-compose.appgarden.yml"
    if not compose_path.exists():
        compose_path = app_path / "docker-compose.yml"
    if not compose_path.exists():
        compose_path = app_path / "docker-compose.yaml"

    if not compose_path.exists():
        raise FileNotFoundError(f"docker-compose file not found in {app_path}")

    with open(compose_path) as f:
        compose_yml = f.read()

    # Extract docker images from compose
    compose_data = yaml.safe_load(compose_yml)
    docker_images = [
        s["image"] for s in compose_data.get("services", {}).values()
        if "image" in s
    ]

    # Build template payload
    template = {
        **metadata,
        "compose_yml": compose_yml,
        "docker_images": docker_images
    }

    log(f"Deploying: {template['name']} v{template['version']}")
    log(f"Images: {docker_images}")

    # Check if template already exists
    response = session.get(f"{url}/api/apps/app_templates", headers=headers)
    response.raise_for_status()

    existing = None
    for t in response.json():
        if t["name"] == template["name"]:
            existing = t
            break

    # Delete existing template if found (PUT has sync issues)
    if existing:
        log(f"Deleting existing template {existing['id']}...")
        del_response = session.delete(
            f"{url}/api/apps/app_templates/{existing['id']}",
            headers=headers
        )
        if del_response.status_code == 409:
            log("Template has active deployments. Stop them first in the Kamiwaza UI.", "ERROR")
            raise RuntimeError("Cannot delete template with active deployments")
        time.sleep(1)  # Brief pause for consistency

    # Create new template
    log("Creating template...")
    response = session.post(
        f"{url}/api/apps/app_templates",
        json=template,
        headers=headers
    )

    if response.status_code != 200:
        log(f"Deployment failed: {response.status_code}", "ERROR")
        log(f"Response: {response.text}", "ERROR")
        raise RuntimeError("Template creation failed")

    result = response.json()
    log(f"Deployed {result['name']} v{result['version']}", "SUCCESS")
    log(f"Template ID: {result['id']}", "SUCCESS")

    return result


def deploy(
    app_path: str,
    url: str | None = None,
    cluster: str | None = None,
    username: str = "admin",
    password: str | None = None,
    skip_build: bool = False,
    skip_push: bool = False,
    dry_run: bool = False,
) -> dict | None:
    """
    Deploy a converted app to a remote Kamiwaza instance.

    Args:
        app_path: Path to app directory (e.g., "apps/my-app")
        url: Kamiwaza instance URL (e.g., "https://192.168.100.118")
        cluster: Predefined cluster name (e.g., "babynator2")
        username: Kamiwaza username
        password: Kamiwaza password
        skip_build: Skip Docker build step
        skip_push: Skip both build and push (deploy existing images)
        dry_run: Show what would be done without making changes

    Returns:
        Deployed template info or None on failure
    """

    log("=" * 60)
    log("  Kamiwaza App Garden Remote Deployer")
    log("=" * 60)

    # Resolve cluster configuration
    if cluster:
        if cluster not in CLUSTERS:
            log(f"Unknown cluster: {cluster}", "ERROR")
            log(f"Available clusters: {', '.join(CLUSTERS.keys())}", "ERROR")
            return None
        cluster_config = CLUSTERS[cluster]
        url = url or cluster_config["url"]
        username = username or cluster_config.get("username", "admin")
        log(f"Using cluster: {cluster} ({cluster_config['description']})")

    if not url:
        log("No URL or cluster specified. Use --url or --cluster", "ERROR")
        return None

    if not password:
        # Try environment variable
        password = os.environ.get("KAMIWAZA_PASSWORD")
        if not password:
            log("No password provided. Use --password or KAMIWAZA_PASSWORD env var", "ERROR")
            return None

    # Resolve app path
    app_path = Path(app_path).resolve()
    if not app_path.exists():
        log(f"App path does not exist: {app_path}", "ERROR")
        return None

    # Find project root (directory containing Makefile)
    project_root = app_path
    while project_root.parent != project_root:
        if (project_root / "Makefile").exists():
            break
        project_root = project_root.parent

    # Load version from kamiwaza.json
    kamiwaza_json = app_path / "kamiwaza.json"
    if kamiwaza_json.exists():
        with open(kamiwaza_json) as f:
            metadata = json.load(f)
        version = metadata.get("version", "1.0.0")
        app_name = metadata.get("name", app_path.name)
    else:
        version = "1.0.0"
        app_name = app_path.name

    log(f"\nApp: {app_name}")
    log(f"Version: {version}")
    log(f"Path: {app_path}")
    log(f"Target: {url}")

    if dry_run:
        log("\n[DRY RUN] Would perform the following:", "WARNING")
        log(f"  1. Build Docker images for {app_name}")
        log("  2. Push images to Docker Hub")
        log("  3. Sync compose files")
        log(f"  4. Deploy template to {url}")
        return None

    try:
        # Step 1: Build and push Docker images
        if not skip_push:
            build_and_push_images(app_path, version, skip_build)
        else:
            log("Skipping build and push (--skip-push)", "WARNING")

        # Step 2: Sync compose files
        sync_compose(project_root)

        # Step 3: Deploy to remote instance
        session = requests.Session()
        session.verify = False  # For self-signed certs

        token = authenticate(session, url, username, password)
        result = deploy_template(session, url, token, app_path)

        log("\n" + "=" * 60)
        log("  Deployment Complete!", "SUCCESS")
        log("=" * 60)
        log(f"\nApp '{result['name']}' v{result['version']} deployed to {url}")
        log(f"Template ID: {result['id']}")
        log(f"\nNext: Open {url} and create a deployment from the template")

        return result

    except Exception as e:
        log(f"\nDeployment failed: {e}", "ERROR")
        return None


def list_clusters():
    """List available predefined clusters."""
    print("\nAvailable clusters:")
    print("-" * 50)
    for name, config in CLUSTERS.items():
        print(f"  {name}")
        print(f"    URL: {config['url']}")
        print(f"    Description: {config['description']}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Deploy Kamiwaza App Garden apps to remote instances"
    )
    parser.add_argument(
        "--app-path", "-a",
        required=False,
        help="Path to app directory (e.g., apps/my-app)"
    )
    parser.add_argument(
        "--url", "-u",
        help="Kamiwaza instance URL (e.g., https://192.168.100.118)"
    )
    parser.add_argument(
        "--cluster", "-c",
        help="Predefined cluster name (e.g., babynator2)"
    )
    parser.add_argument(
        "--username",
        default="admin",
        help="Kamiwaza username (default: admin)"
    )
    parser.add_argument(
        "--password", "-p",
        help="Kamiwaza password (or use KAMIWAZA_PASSWORD env var)"
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip Docker build, only push existing images"
    )
    parser.add_argument(
        "--skip-push",
        action="store_true",
        help="Skip both build and push, deploy existing images"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    parser.add_argument(
        "--list-clusters",
        action="store_true",
        help="List available predefined clusters"
    )

    args = parser.parse_args()

    if args.list_clusters:
        list_clusters()
        return

    if not args.app_path:
        parser.print_help()
        print("\nError: --app-path is required")
        sys.exit(1)

    result = deploy(
        app_path=args.app_path,
        url=args.url,
        cluster=args.cluster,
        username=args.username,
        password=args.password,
        skip_build=args.skip_build,
        skip_push=args.skip_push,
        dry_run=args.dry_run,
    )

    if result is None and not args.dry_run:
        sys.exit(1)


if __name__ == "__main__":
    main()
