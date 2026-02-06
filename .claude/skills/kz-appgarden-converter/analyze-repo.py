#!/usr/bin/env python3
"""
Analyze a GitHub repository or local project for Kamiwaza App Garden compatibility.

Usage:
    python analyze-repo.py <path-or-url>
    python analyze-repo.py https://github.com/user/repo
    python analyze-repo.py /path/to/local/project
"""

import json
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AnalysisResult:
    """Result of repository analysis."""

    # Basic info
    name: str = ""
    path: str = ""

    # Project type detection
    project_type: str = "unknown"  # python, nodejs, go, rust, ruby, unknown
    framework: str = ""  # fastapi, flask, express, nextjs, etc.

    # Architecture
    architecture: str = "unknown"  # single, frontend-backend, multi-service
    has_frontend: bool = False
    has_backend: bool = False

    # Docker status
    has_dockerfile: bool = False
    has_docker_compose: bool = False

    # Compatibility issues
    issues: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    # Compatibility score (0-10)
    score: int = 0

    # Recommended extension type
    recommended_type: str = "app"  # app, service, tool

    # Suggested transformations
    transformations: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "path": self.path,
            "project_type": self.project_type,
            "framework": self.framework,
            "architecture": self.architecture,
            "has_frontend": self.has_frontend,
            "has_backend": self.has_backend,
            "has_dockerfile": self.has_dockerfile,
            "has_docker_compose": self.has_docker_compose,
            "issues": self.issues,
            "warnings": self.warnings,
            "score": self.score,
            "recommended_type": self.recommended_type,
            "transformations": self.transformations,
            "compatible": len(self.issues) == 0,
        }


def clone_repo(url: str) -> str:
    """Clone a GitHub repository to a temporary directory."""
    tmpdir = tempfile.mkdtemp(prefix="kamiwaza-analyze-")
    subprocess.run(
        ["git", "clone", "--depth", "1", url, tmpdir],
        check=True,
        capture_output=True,
    )
    return tmpdir


def detect_project_type(path: Path) -> tuple[str, str]:
    """Detect the project type and framework."""

    # Python
    if (path / "requirements.txt").exists() or (path / "pyproject.toml").exists():
        framework = ""
        for f in path.rglob("*.py"):
            content = f.read_text(errors="ignore")
            if "fastapi" in content.lower() or "FastAPI" in content:
                framework = "fastapi"
                break
            elif "flask" in content.lower() or "Flask" in content:
                framework = "flask"
                break
            elif "streamlit" in content.lower():
                framework = "streamlit"
                break
            elif "gradio" in content.lower():
                framework = "gradio"
                break
        return "python", framework

    # Node.js
    if (path / "package.json").exists():
        try:
            pkg = json.loads((path / "package.json").read_text())
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

            if "next" in deps:
                return "nodejs", "nextjs"
            elif "express" in deps:
                return "nodejs", "express"
            elif "fastify" in deps:
                return "nodejs", "fastify"
            elif "react" in deps:
                return "nodejs", "react"
            elif "vue" in deps:
                return "nodejs", "vue"
        except (json.JSONDecodeError, KeyError):
            pass
        return "nodejs", ""

    # Go
    if (path / "go.mod").exists():
        content = (path / "go.mod").read_text(errors="ignore")
        if "gin-gonic" in content:
            return "go", "gin"
        elif "echo" in content:
            return "go", "echo"
        return "go", ""

    # Rust
    if (path / "Cargo.toml").exists():
        content = (path / "Cargo.toml").read_text(errors="ignore")
        if "actix" in content:
            return "rust", "actix"
        elif "axum" in content:
            return "rust", "axum"
        return "rust", ""

    # Ruby
    if (path / "Gemfile").exists():
        content = (path / "Gemfile").read_text(errors="ignore")
        if "rails" in content.lower():
            return "ruby", "rails"
        elif "sinatra" in content.lower():
            return "ruby", "sinatra"
        return "ruby", ""

    return "unknown", ""


def detect_architecture(path: Path) -> tuple[str, bool, bool]:
    """Detect the project architecture."""

    has_frontend = False
    has_backend = False

    # Check for frontend directory
    frontend_dirs = ["frontend", "client", "web", "ui", "app"]
    for d in frontend_dirs:
        if (path / d).is_dir():
            # Check if it has frontend files
            frontend_path = path / d
            if (frontend_path / "package.json").exists():
                has_frontend = True
                break
            if list(frontend_path.glob("*.html")) or list(frontend_path.glob("*.tsx")):
                has_frontend = True
                break

    # Check for backend directory
    backend_dirs = ["backend", "server", "api", "src"]
    for d in backend_dirs:
        if (path / d).is_dir():
            backend_path = path / d
            # Check for backend indicators
            if (backend_path / "requirements.txt").exists():
                has_backend = True
                break
            if (backend_path / "package.json").exists():
                pkg_path = backend_path / "package.json"
                try:
                    pkg = json.loads(pkg_path.read_text())
                    deps = pkg.get("dependencies", {})
                    if any(d in deps for d in ["express", "fastify", "koa", "hapi"]):
                        has_backend = True
                        break
                except (json.JSONDecodeError, KeyError):
                    pass
            if list(backend_path.glob("*.py")) or list(backend_path.glob("*.go")):
                has_backend = True
                break

    # If no explicit frontend/backend, check root
    if not has_frontend and not has_backend:
        # Check if it's a single service
        if (path / "package.json").exists():
            try:
                pkg = json.loads((path / "package.json").read_text())
                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                if any(d in deps for d in ["express", "fastify", "koa"]):
                    has_backend = True
                if any(d in deps for d in ["react", "vue", "next", "svelte"]):
                    has_frontend = True
            except (json.JSONDecodeError, KeyError):
                pass

        if (path / "requirements.txt").exists() or (path / "pyproject.toml").exists():
            has_backend = True

    # Determine architecture
    if has_frontend and has_backend:
        architecture = "frontend-backend"
    elif has_frontend:
        architecture = "frontend-only"
    elif has_backend:
        architecture = "backend-only"
    else:
        architecture = "unknown"

    return architecture, has_frontend, has_backend


def check_docker_files(path: Path) -> tuple[bool, bool]:
    """Check for Docker files."""
    has_dockerfile = (path / "Dockerfile").exists()
    has_compose = (
        (path / "docker-compose.yml").exists() or
        (path / "docker-compose.yaml").exists()
    )
    return has_dockerfile, has_compose


def check_compatibility_issues(path: Path) -> tuple[list, list, list]:
    """Check for App Garden compatibility issues."""
    issues = []  # Blocking issues
    warnings = []  # Non-blocking warnings
    transformations = []  # Required transformations

    # Check docker-compose for issues
    compose_file = None
    for name in ["docker-compose.yml", "docker-compose.yaml"]:
        if (path / name).exists():
            compose_file = path / name
            break

    if compose_file:
        content = compose_file.read_text(errors="ignore")

        # Check for host port bindings
        if re.search(r'ports:\s*\n\s*-\s*["\']?\d+:\d+', content):
            transformations.append("Convert port bindings from '8000:8000' to '8000'")

        # Check for bind mounts
        if re.search(r'volumes:\s*\n\s*-\s*\./', content):
            transformations.append("Convert bind mounts to named volumes")

        # Check for host network
        if "network_mode: host" in content or 'network_mode: "host"' in content:
            issues.append("Host network mode is not supported")

        # Check for privileged mode
        if "privileged: true" in content:
            issues.append("Privileged containers are not supported")

        # Check for resource limits
        if "resources:" not in content or "limits:" not in content:
            transformations.append("Add resource limits (cpus, memory)")

    # Check for health endpoint
    has_health = False
    for pattern in ["*.py", "*.js", "*.ts", "*.go"]:
        for f in path.rglob(pattern):
            try:
                content = f.read_text(errors="ignore")
                if "/health" in content or '"/health"' in content or "'/health'" in content:
                    has_health = True
                    break
            except Exception:
                continue
        if has_health:
            break

    if not has_health:
        transformations.append("Add /health endpoint for health checks")

    # Check for localhost references in code
    localhost_refs = []
    for pattern in ["*.py", "*.js", "*.ts", "*.go", "*.env", "*.env.*"]:
        for f in path.rglob(pattern):
            try:
                content = f.read_text(errors="ignore")
                if re.search(r'localhost:\d+', content):
                    localhost_refs.append(str(f.relative_to(path)))
            except Exception:
                continue

    if localhost_refs:
        warnings.append(f"Found localhost references in: {', '.join(localhost_refs[:3])}")
        transformations.append("Replace localhost URLs with Docker service names")

    # Check for GUI dependencies
    gui_indicators = ["electron", "qt", "gtk", "tkinter", "pygame"]
    for f in [path / "package.json", path / "requirements.txt", path / "pyproject.toml"]:
        if f.exists():
            content = f.read_text(errors="ignore").lower()
            for gui in gui_indicators:
                if gui in content:
                    issues.append(f"GUI dependency detected ({gui}) - desktop apps not supported")
                    break

    return issues, warnings, transformations


def calculate_score(result: AnalysisResult) -> int:
    """Calculate compatibility score (0-10)."""
    score = 0

    # Docker files (+4 points)
    if result.has_dockerfile:
        score += 2
    if result.has_docker_compose:
        score += 2

    # Web-based architecture (+2 points)
    if result.architecture in ["frontend-backend", "backend-only", "frontend-only"]:
        score += 2

    # No blocking issues (+2 points)
    if len(result.issues) == 0:
        score += 2

    # Known framework (+1 point)
    if result.framework:
        score += 1

    # Few transformations needed (+1 point)
    if len(result.transformations) <= 2:
        score += 1

    return min(score, 10)


def recommend_extension_type(result: AnalysisResult) -> str:
    """Recommend the extension type based on analysis."""

    # If it's a CLI tool or utility, recommend tool
    if result.project_type == "python":
        # Check for CLI indicators
        has_cli = False
        path = Path(result.path)
        for f in ["cli.py", "main.py", "__main__.py"]:
            if (path / f).exists():
                content = (path / f).read_text(errors="ignore")
                if "argparse" in content or "click" in content or "typer" in content:
                    has_cli = True
                    break
        if has_cli and not result.has_frontend:
            return "tool"

    # If it's infrastructure (database, cache, etc.), recommend service
    service_indicators = ["postgres", "redis", "mongo", "mysql", "milvus", "qdrant"]
    if result.has_docker_compose:
        path = Path(result.path)
        for name in ["docker-compose.yml", "docker-compose.yaml"]:
            if (path / name).exists():
                content = (path / name).read_text(errors="ignore").lower()
                for indicator in service_indicators:
                    if indicator in content:
                        return "service"

    # Default to app
    return "app"


def analyze_repository(path_or_url: str) -> AnalysisResult:
    """Analyze a repository for Kamiwaza compatibility."""

    result = AnalysisResult()

    # Handle URL vs local path
    if path_or_url.startswith("http") or path_or_url.startswith("git@"):
        print(f"Cloning repository: {path_or_url}", file=sys.stderr)
        path = Path(clone_repo(path_or_url))
        result.name = path_or_url.split("/")[-1].replace(".git", "")
    else:
        path = Path(path_or_url).resolve()
        result.name = path.name

    result.path = str(path)

    # Detect project type
    result.project_type, result.framework = detect_project_type(path)

    # Detect architecture
    result.architecture, result.has_frontend, result.has_backend = detect_architecture(path)

    # Check Docker files
    result.has_dockerfile, result.has_docker_compose = check_docker_files(path)

    # Check compatibility
    result.issues, result.warnings, result.transformations = check_compatibility_issues(path)

    # Calculate score
    result.score = calculate_score(result)

    # Recommend extension type
    result.recommended_type = recommend_extension_type(result)

    return result


def print_report(result: AnalysisResult):
    """Print a human-readable analysis report."""

    print("\n" + "=" * 60)
    print(f"  Repository Analysis: {result.name}")
    print("=" * 60)

    print(f"\nProject Type: {result.project_type}")
    if result.framework:
        print(f"Framework: {result.framework}")
    print(f"Architecture: {result.architecture}")

    print("\nDocker Status:")
    print(f"  Dockerfile: {'Yes' if result.has_dockerfile else 'No'}")
    print(f"  docker-compose: {'Yes' if result.has_docker_compose else 'No'}")

    print(f"\nCompatibility Score: {result.score}/10", end="")
    if result.score >= 8:
        print(" (Easy conversion)")
    elif result.score >= 5:
        print(" (Moderate work needed)")
    else:
        print(" (Significant work needed)")

    print(f"\nRecommended Extension Type: {result.recommended_type}")

    if result.issues:
        print("\n[BLOCKING ISSUES]")
        for issue in result.issues:
            print(f"  - {issue}")

    if result.warnings:
        print("\n[WARNINGS]")
        for warning in result.warnings:
            print(f"  - {warning}")

    if result.transformations:
        print("\n[REQUIRED TRANSFORMATIONS]")
        for i, t in enumerate(result.transformations, 1):
            print(f"  {i}. {t}")

    compatible = len(result.issues) == 0
    print("\n" + "-" * 60)
    if compatible:
        print("RESULT: Compatible with App Garden")
        print("\nNext steps:")
        print(f"  1. make new TYPE={result.recommended_type} NAME={result.name}")
        print("  2. Copy project files to the new extension directory")
        print("  3. Apply the required transformations above")
        print("  4. make sync-compose && make validate")
    else:
        print("RESULT: NOT compatible with App Garden")
        print("\nThe blocking issues above must be resolved before conversion.")
    print("=" * 60 + "\n")


def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze-repo.py <path-or-url>")
        print("  path-or-url: GitHub URL or local path to analyze")
        sys.exit(1)

    path_or_url = sys.argv[1]

    # Check for --json flag
    output_json = "--json" in sys.argv

    result = analyze_repository(path_or_url)

    if output_json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print_report(result)


if __name__ == "__main__":
    main()
