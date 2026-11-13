"""Allocate and clean only the temporary directory owned by this process run."""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
import logging
import shutil
import tempfile

logger = logging.getLogger("lumalab")


@contextmanager
def temporary_storage(root: Path) -> Iterator[Path]:
    try:
        root = root.resolve()
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        directory = Path(tempfile.mkdtemp(prefix="lumalab-run-", dir=root)).resolve()
    except OSError:
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
