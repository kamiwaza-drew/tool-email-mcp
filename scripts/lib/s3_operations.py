"""S3/R2 operations for registry management.

Provides download, upload, and locking functionality for the extension registry.
"""

import json
import os
import socket
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def get_s3_endpoint() -> str | None:
    """Get the S3 endpoint URL from environment."""
    endpoint = os.getenv("KAMIWAZA_REGISTRY_ENDPOINT")
    if not endpoint:
        # Check for R2 account ID to construct endpoint
        account_id = os.getenv("KAMIWAZA_REGISTRY_ACCOUNT_ID")
        if account_id:
            endpoint = f"https://{account_id}.r2.cloudflarestorage.com"
    return endpoint


def configure_aws_profile(stage: str) -> str | None:
    """Ensure a stage-specific AWS profile is set for registry operations."""
    stage_upper = stage.upper()
    stage_profile = os.getenv(f"AWS_PROFILE_{stage_upper}")
    if not stage_profile:
        raise ValueError(f"AWS_PROFILE_{stage_upper} is not set. Configure a per-stage profile for stage '{stage}'.")

    os.environ["AWS_PROFILE"] = stage_profile
    return stage_profile


def get_bucket_for_stage(stage: str) -> str:
    """Get the bucket name for the given stage."""
    configure_aws_profile(stage)
    stage_upper = stage.upper()
    bucket = os.getenv(f"KAMIWAZA_REGISTRY_BUCKET_{stage_upper}")
    if not bucket:
        bucket = os.getenv("KAMIWAZA_REGISTRY_BUCKET")
    if not bucket:
        raise ValueError(
            f"No bucket configured for stage '{stage}'. "
            f"Set KAMIWAZA_REGISTRY_BUCKET_{stage_upper} or KAMIWAZA_REGISTRY_BUCKET"
        )
    return bucket


def get_aws_cli_args() -> list[str]:
    """Get common AWS CLI arguments for S3 operations."""
    args = []
    endpoint = get_s3_endpoint()
    if endpoint:
        args.extend(["--endpoint-url", endpoint])
    region = os.getenv("KAMIWAZA_REGISTRY_REGION")
    if region:
        args.extend(["--region", region])
    return args


def s3_path(bucket: str, path: str) -> str:
    """Construct an S3 path."""
    path = path.lstrip("/")
    return f"s3://{bucket}/{path}"


def run_aws_command(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run an AWS CLI command."""
    cmd = ["aws"] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise RuntimeError(f"AWS CLI command failed: {' '.join(cmd)}\nstdout: {result.stdout}\nstderr: {result.stderr}")
    return result


def lock_s3_path(bucket: str, garden_dir: str | None = None) -> str:
    """Construct the S3 path for the registry lock file."""
    lock_name = os.getenv("KAMIWAZA_REGISTRY_LOCK_NAME", "registry.lock")
    if garden_dir:
        return s3_path(bucket, f"garden/{garden_dir}/{lock_name}")
    return s3_path(bucket, lock_name)


def check_lock_exists(bucket: str, garden_dir: str | None = None) -> bool:
    """Check if a lock file exists in the bucket."""
    lock_path = lock_s3_path(bucket, garden_dir)
    args = get_aws_cli_args() + ["s3", "ls", lock_path]
    result = run_aws_command(args, check=False)
    return result.returncode == 0 and ".lock" in result.stdout


def get_lock_info(bucket: str, garden_dir: str | None = None) -> dict | None:
    """Get lock file contents if it exists."""
    if not check_lock_exists(bucket, garden_dir):
        return None

    lock_path = lock_s3_path(bucket, garden_dir)
    args = get_aws_cli_args() + ["s3", "cp", lock_path, "-"]
    result = run_aws_command(args, check=False)
    if result.returncode != 0:
        return None

    try:
        data: dict = json.loads(result.stdout)
        return data
    except json.JSONDecodeError:
        return {"raw": result.stdout}


def acquire_lock(bucket: str, garden_dir: str | None = None, owner: str | None = None) -> bool:
    """Acquire a lock on the registry bucket.

    Args:
        bucket: S3 bucket name
        garden_dir: Optional garden directory to scope the lock
        owner: Optional owner identifier (defaults to CI job ID or hostname)

    Returns:
        True if lock acquired, False if lock already exists

    Raises:
        RuntimeError if lock exists (with details about existing lock)
    """
    # Check if lock already exists
    existing_lock = get_lock_info(bucket, garden_dir)
    if existing_lock:
        raise RuntimeError(
            f"Lock already exists in bucket '{bucket}'.\n"
            f"Lock info: {json.dumps(existing_lock, indent=2)}\n"
            f"Manual investigation required. Remove lock with:\n"
            f"  aws s3 rm {lock_s3_path(bucket, garden_dir)}"
        )

    # Create lock content
    if owner is None:
        owner = os.getenv("CI_JOB_ID") or os.getenv("GITHUB_RUN_ID") or "manual"

    lock_content = {
        "owner": owner,
        "hostname": socket.gethostname(),
        "acquired_at": datetime.now(timezone.utc).isoformat(),
        "pid": os.getpid(),
    }

    # Write lock file
    lock_json = json.dumps(lock_content, indent=2)
    lock_path = lock_s3_path(bucket, garden_dir)

    # Write lock content to a temporary file to avoid stdin streaming issues.
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp:
        tmp.write(lock_json)
        tmp.flush()
        tmp_path = tmp.name

    try:
        lock_key = lock_path.replace(f"s3://{bucket}/", "")
        args = get_aws_cli_args() + [
            "s3api",
            "put-object",
            "--bucket",
            bucket,
            "--key",
            lock_key,
            "--body",
            tmp_path,
        ]
        result = run_aws_command(args, check=False)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    if result.returncode != 0:
        raise RuntimeError(f"Failed to create lock: {result.stderr}")

    print(f"Lock acquired: {lock_path}")
    return True


def release_lock(bucket: str, garden_dir: str | None = None) -> bool:
    """Release the lock on the registry bucket.

    Args:
        bucket: S3 bucket name
        garden_dir: Optional garden directory to scope the lock

    Returns:
        True if lock released, False if no lock existed
    """
    if not check_lock_exists(bucket, garden_dir):
        print("No lock to release")
        return False

    lock_path = lock_s3_path(bucket, garden_dir)
    args = get_aws_cli_args() + ["s3", "rm", lock_path]
    result = run_aws_command(args, check=False)

    if result.returncode == 0:
        print(f"Lock released: {lock_path}")
        return True
    else:
        print(f"Warning: Failed to release lock: {result.stderr}")
        return False


def download_registry(
    bucket: str, garden_dir: str, local_path: Path, create_backup: bool = True
) -> tuple[Path, Path | None]:
    """Download the registry from S3.

    Args:
        bucket: S3 bucket name
        garden_dir: Garden directory name (v2 or default)
        local_path: Local path to download to
        create_backup: Whether to create a timestamped backup

    Returns:
        Tuple of (working_path, backup_path)
    """
    remote_path = s3_path(bucket, f"garden/{garden_dir}/")
    working_path = local_path / "remote" / garden_dir
    backup_path = None

    # Create working directory
    working_path.mkdir(parents=True, exist_ok=True)

    # Download registry
    args = get_aws_cli_args() + [
        "s3",
        "sync",
        remote_path,
        str(working_path),
    ]

    print(f"Downloading registry from {remote_path}...")
    result = run_aws_command(args, check=False)

    if result.returncode != 0:
        # Check if it's just an empty bucket (no objects)
        if "NoSuchKey" in result.stderr or not result.stderr.strip():
            print("Remote registry is empty (first publish)")
        else:
            raise RuntimeError(f"Failed to download registry: {result.stderr}")

    # Create backup if requested
    if create_backup:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = local_path / "backups" / garden_dir / timestamp
        backup_path.mkdir(parents=True, exist_ok=True)

        # Copy downloaded content to backup
        if working_path.exists() and any(working_path.iterdir()):
            import shutil

            shutil.copytree(working_path, backup_path, dirs_exist_ok=True)
            print(f"Backup created: {backup_path}")

    return working_path, backup_path


def upload_registry(bucket: str, garden_dir: str, local_path: Path, delete: bool = True) -> bool:
    """Upload the registry to S3.

    Args:
        bucket: S3 bucket name
        garden_dir: Garden directory name (v2 or default)
        local_path: Local path containing the registry
        delete: Whether to delete remote files not in local

    Returns:
        True if upload succeeded
    """
    remote_path = s3_path(bucket, f"garden/{garden_dir}/")

    args = get_aws_cli_args() + [
        "s3",
        "sync",
        str(local_path),
        remote_path,
    ]

    if delete:
        args.append("--delete")

    print(f"Uploading registry to {remote_path}...")
    run_aws_command(args)

    print(f"Registry uploaded to {remote_path}")
    return True


def restore_backup(bucket: str, garden_dir: str, backup_path: Path) -> bool:
    """Restore a backup to S3.

    Args:
        bucket: S3 bucket name
        garden_dir: Garden directory name (v2 or default)
        backup_path: Path to backup directory

    Returns:
        True if restore succeeded
    """
    if not backup_path.exists():
        raise ValueError(f"Backup path does not exist: {backup_path}")

    print(f"Restoring backup from {backup_path}...")
    return upload_registry(bucket, garden_dir, backup_path, delete=True)


def verify_upload(bucket: str, garden_dir: str, local_path: Path) -> bool:
    """Verify that the upload matches local state.

    Args:
        bucket: S3 bucket name
        garden_dir: Garden directory name
        local_path: Local path that was uploaded

    Returns:
        True if verification passed
    """
    import filecmp
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        verify_path = Path(tmpdir) / garden_dir
        verify_path.mkdir(parents=True)

        remote_path = s3_path(bucket, f"garden/{garden_dir}/")
        args = get_aws_cli_args() + [
            "s3",
            "sync",
            remote_path,
            str(verify_path),
        ]

        print("Verifying upload...")
        run_aws_command(args)

        # Compare apps.json and tools.json
        for filename in ["apps.json", "tools.json"]:
            local_file = local_path / filename
            remote_file = verify_path / filename

            if local_file.exists() and remote_file.exists():
                if not filecmp.cmp(local_file, remote_file, shallow=False):
                    print(f"Verification failed: {filename} mismatch")
                    return False
            elif local_file.exists() != remote_file.exists():
                print(f"Verification failed: {filename} missing")
                return False

        print("Verification passed")
        return True


if __name__ == "__main__":
    # Simple test/debug functionality
    import argparse

    parser = argparse.ArgumentParser(description="S3 operations for registry")
    parser.add_argument("--stage", default="dev", help="Stage (dev/stage/prod)")
    parser.add_argument(
        "--garden-dir",
        default=None,
        help="Garden directory name (e.g., v2 or default) to scope locks",
    )
    parser.add_argument("--check-lock", action="store_true", help="Check if lock exists")
    parser.add_argument("--acquire-lock", action="store_true", help="Acquire lock")
    parser.add_argument("--release-lock", action="store_true", help="Release lock")

    args = parser.parse_args()
    bucket = get_bucket_for_stage(args.stage)

    if args.check_lock:
        lock_info = get_lock_info(bucket, args.garden_dir)
        if lock_info:
            print(f"Lock exists: {json.dumps(lock_info, indent=2)}")
        else:
            print("No lock found")
    elif args.acquire_lock:
        acquire_lock(bucket, args.garden_dir)
    elif args.release_lock:
        release_lock(bucket, args.garden_dir)
