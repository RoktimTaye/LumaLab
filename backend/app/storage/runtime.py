"""Allocate and clean only the temporary directory owned by this process run."""

from collections.abc import Iterator
from contextlib import contextmanager
import csv
import os
from pathlib import Path
import logging
import shutil
import subprocess
import tempfile
import time

logger = logging.getLogger("lumalab")


def restrict_directory(directory: Path) -> None:
    if os.name != "nt":
        directory.chmod(0o700)
        return
    # Python 3.11.9 ignores Windows mkdir(mode=0o700); protect this run only.
    system = Path(os.environ["SystemRoot"]) / "System32"
    try:
        owner = subprocess.run([str(system / "whoami.exe"), "/user", "/fo", "csv", "/nh"],
                               check=True, capture_output=True, text=True, timeout=5)
        rows = list(csv.reader(owner.stdout.splitlines()))
        if len(rows) != 1 or len(rows[0]) != 2 or not rows[0][1].startswith("S-1-"):
            raise OSError("Unable to identify the storage account.")
        subprocess.run([str(system / "icacls.exe"), str(directory), "/inheritance:r",
                        "/grant:r", f"*{rows[0][1]}:(OI)(CI)F", "/q"],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
    except subprocess.SubprocessError:
        raise OSError("Unable to restrict private storage access.") from None


def remove_stale_runs(root: Path, ttl_seconds: int) -> None:
    cutoff = time.time() - ttl_seconds
    for candidate in root.glob("lumalab-run-*"):
        if candidate.is_symlink() or not candidate.is_dir() or candidate.parent != root:
            continue
        if candidate.stat().st_mtime <= cutoff:
            shutil.rmtree(candidate)


@contextmanager
def temporary_storage(root: Path, ttl_seconds: int = 3_600) -> Iterator[Path]:
    directory = None
    try:
        root = root.resolve()
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        remove_stale_runs(root, ttl_seconds)
        directory = Path(tempfile.mkdtemp(prefix="lumalab-run-", dir=root)).resolve()
        restrict_directory(directory)
    except OSError:
        if directory is not None and directory.parent == root:
            shutil.rmtree(directory, ignore_errors=True)
        logger.error("storage_start_failed")
        raise RuntimeError("Unable to initialize private temporary storage; check TEMP_IMAGE_DIR and permissions.") from None
    try:
        yield directory
    finally:
        # Never recursively remove a substituted path or the configured storage root.
        if directory.resolve() != directory or directory.parent != root:
            logger.error("storage_cleanup_failed")
            raise RuntimeError("Temporary storage cleanup refused an unexpected directory.")
        try:
            shutil.rmtree(directory)
        except OSError:
            logger.error("storage_cleanup_failed")
            raise RuntimeError("Unable to clean the temporary storage directory.") from None


def storage_available(directory: Path | None) -> bool:
    if directory is None:
        return False
    try:
        if directory.resolve() != directory:
            return False
        with tempfile.NamedTemporaryFile(mode="w+b", prefix=".health-", dir=directory) as probe:
            probe.write(b"ok")
            probe.flush()
            probe.seek(0)
            return probe.read() == b"ok"
    except OSError:
        return False
