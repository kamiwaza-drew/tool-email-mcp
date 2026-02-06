#!/usr/bin/env python3
"""
Validate docker-compose files for App Garden compatibility.

This script checks docker-compose.appgarden.yml files to ensure they
follow App Garden requirements:
- No host port mappings
- No bind mounts
- Only named volumes
- Required extra_hosts
- Accessible images
- Resource limits defined
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Any

import yaml


def load_compose_file(file_path: Path) -> tuple[dict[str, Any], str]:
    """Load and parse a docker-compose YAML file. Returns (data, error_message)."""
    try:
        with open(file_path) as f:
            return yaml.safe_load(f), None
    except yaml.YAMLError as e:
        return None, f"Invalid YAML: {e}"
    except Exception as e:
        return None, f"Error reading file: {e}"


def validate_ports(ports: list[Any], service_name: str) -> list[str]:
    """Validate port configuration."""
    errors = []

    for port in ports:
        if isinstance(port, str):
            # Check for host port mapping
            if ":" in port and not port.startswith(":"):
                errors.append(
                    f"Service '{service_name}': Port mapping '{port}' includes host port. Use only container port."
                )
        elif isinstance(port, dict):
            # Long form port definition
            if "published" in port:
                errors.append(f"Service '{service_name}': Port has 'published' field (host port). Remove it.")

    return errors


def validate_volumes(volumes: list[Any], service_name: str) -> list[str]:
    """Validate volume configuration."""
    errors = []

    for volume in volumes:
        if isinstance(volume, str):
            # Check for bind mounts
            if (volume.startswith("/") or volume.startswith("./") or volume.startswith("../")) or (
                ":" in volume and ("/" in volume.split(":")[0] or "\\" in volume.split(":")[0])
            ):
                errors.append(f"Service '{service_name}': Bind mount detected: '{volume}'. Only named volumes allowed.")
        elif isinstance(volume, dict):
            # Long form volume definition
            if "type" in volume and volume["type"] == "bind":
                errors.append(f"Service '{service_name}': Bind mount detected. Only named volumes allowed.")

    return errors


def validate_service(service: dict[str, Any], service_name: str) -> list[str]:
    """Validate a single service configuration."""
    errors = []

    # Check ports
    if "ports" in service:
        errors.extend(validate_ports(service["ports"], service_name))

    # Check volumes
    if "volumes" in service:
        errors.extend(validate_volumes(service["volumes"], service_name))

    # Check for build context
    if "build" in service:
        errors.append(f"Service '{service_name}': Has 'build' section. Must use pre-built images only.")

    # Check for required extra_hosts (for services that need Kamiwaza access)
    if "environment" in service:
        env_vars = service["environment"]
        needs_host = False

        # Check if service references Kamiwaza endpoints
        if isinstance(env_vars, list):
            for var in env_vars:
                if isinstance(var, str) and "host.docker.internal" in var:
                    needs_host = True
                    break
        elif isinstance(env_vars, dict):
            for _key, value in env_vars.items():
                if value and "host.docker.internal" in str(value):
                    needs_host = True
                    break

        if needs_host:
            if "extra_hosts" not in service:
                errors.append(f"Service '{service_name}': References host.docker.internal but missing extra_hosts")
            else:
                has_correct_entry = False
                for host in service["extra_hosts"]:
                    if "host.docker.internal:host-gateway" in host:
                        has_correct_entry = True
                        break
                if not has_correct_entry:
                    errors.append(
                        f"Service '{service_name}': Missing 'host.docker.internal:host-gateway' in extra_hosts"
                    )

    # Check for resource limits
    if (
        "deploy" not in service
        or "resources" not in service["deploy"]
        or "limits" not in service["deploy"]["resources"]
    ):
        errors.append(f"Service '{service_name}': Missing resource limits (deploy.resources.limits)")

    # Check image format
    if "image" in service:
        image = service["image"]
        if not isinstance(image, str):
            errors.append(f"Service '{service_name}': Image must be a string")
        # Basic image format validation
        elif not re.match(r"^[\w\-\./]+(:\w[\w\-\.]*)?(@sha256:[a-f0-9]{64})?$", image):
            errors.append(f"Service '{service_name}': Invalid image format: '{image}'")

    return errors


def validate_compose(compose_data: dict[str, Any]) -> list[str]:
    """Validate entire compose file."""
    errors = []

    if not compose_data:
        errors.append("Empty compose file")
        return errors

    if "services" not in compose_data:
        errors.append("No 'services' section found")
        return errors

    # Validate each service
    for service_name, service in compose_data["services"].items():
        if not isinstance(service, dict):
            errors.append(f"Service '{service_name}': Invalid service definition")
            continue
        errors.extend(validate_service(service, service_name))

    # Validate volumes section
    if "volumes" in compose_data:
        for volume_name, volume_config in compose_data["volumes"].items():
            if volume_config is not None and isinstance(volume_config, dict):
                if "driver_opts" in volume_config:
                    # Check for potential host path references
                    driver_opts = volume_config["driver_opts"]
                    if isinstance(driver_opts, dict):
                        for opt_key, opt_value in driver_opts.items():
                            if "device" in opt_key and ("/" in str(opt_value) or "\\" in str(opt_value)):
                                errors.append(f"Volume '{volume_name}': driver_opts may reference host path")

    return errors


def check_extension(extension_path: Path, extension_type: str) -> tuple[str, list[str]]:
    """Check a single extension's docker-compose.appgarden.yml file."""
    compose_path = extension_path / "docker-compose.appgarden.yml"

    # Also check for regular docker-compose.yml as fallback
    if not compose_path.exists():
        compose_path = extension_path / "docker-compose.yml"
        if not compose_path.exists():
            return extension_path.name, ["No docker-compose file found"]
        else:
            return extension_path.name, ["Missing docker-compose.appgarden.yml (using docker-compose.yml)"]

    compose_data, error = load_compose_file(compose_path)
    if error:
        return extension_path.name, [error]

    errors = validate_compose(compose_data)
    return extension_path.name, errors


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Validate docker-compose files")
    parser.add_argument("--type", choices=["app", "service", "tool"], help="Extension type")
    parser.add_argument("--name", help="Extension name")
    args = parser.parse_args()

    # Get the repository root
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent

    total_errors = 0

    # If specific extension requested
    if args.type and args.name:
        ext_path = repo_root / f"{args.type}s" / args.name
        if not ext_path.exists():
            print(f"❌ Extension not found: {args.type}s/{args.name}")
            sys.exit(1)

        print(f"Validating docker-compose for {args.type}/{args.name}...")
        print("=" * 50)

        name, errors = check_extension(ext_path, f"{args.type}s")
        if errors:
            print(f"\n❌ {args.type}s/{name}:")
            for error in errors:
                print(f"   - {error}")
            total_errors += len(errors)
        else:
            print(f"✅ {args.type}s/{name}")
    else:
        # Validate all extensions
        print("Validating docker-compose files for App Garden...")
        print("=" * 50)

        # Check apps
        print("\nValidating apps...")
        apps_path = repo_root / "apps"
        if apps_path.exists():
            for app_dir in sorted(apps_path.iterdir()):
                if app_dir.is_dir() and not app_dir.name.startswith("."):
                    name, errors = check_extension(app_dir, "apps")
                    if errors:
                        print(f"\n❌ apps/{name}:")
                        for error in errors:
                            print(f"   - {error}")
                            total_errors += 1
                    else:
                        print(f"✅ apps/{name}")

        # Check services
        print("\nValidating services...")
        services_path = repo_root / "services"
        if services_path.exists():
            for service_dir in sorted(services_path.iterdir()):
                if service_dir.is_dir() and not service_dir.name.startswith("."):
                    name, errors = check_extension(service_dir, "services")
                    if errors:
                        print(f"\n❌ services/{name}:")
                        for error in errors:
                            print(f"   - {error}")
                            total_errors += 1
                    else:
                        print(f"✅ services/{name}")

        # Check tools
        print("\nValidating tools...")
        tools_path = repo_root / "tools"
        if tools_path.exists():
            for tool_dir in sorted(tools_path.iterdir()):
                if tool_dir.is_dir() and not tool_dir.name.startswith("."):
                    name, errors = check_extension(tool_dir, "tools")
                    if errors:
                        print(f"\n❌ tools/{name}:")
                        for error in errors:
                            print(f"   - {error}")
                            total_errors += 1
                    else:
                        print(f"✅ tools/{name}")

    # Summary
    print("\n" + "=" * 50)
    if total_errors > 0:
        print(f"❌ Validation failed with {total_errors} error(s)")
        sys.exit(1)
    else:
        print("✅ All docker-compose files are valid for App Garden!")


if __name__ == "__main__":
    main()
