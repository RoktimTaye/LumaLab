"""Standalone 24 MP export benchmark; run in a fresh process for peak RSS."""

import json
import os
from pathlib import Path
import tempfile
from time import perf_counter

from PIL import Image

from app.config import Settings
from app.schemas.images import Adjustments
from app.services.images import render


def peak_rss_bytes():
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
                (name, ctypes.c_size_t) for name in (
                    "PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage", "QuotaPagedPoolUsage",
                    "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage")]
        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        ctypes.windll.kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        ctypes.windll.psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        if not ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
            raise OSError("Unable to measure process memory")
        return counters.PeakWorkingSetSize
    import resource
    import sys
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == "darwin" else 1024)


def main():
    settings = Settings(_env_file=None, database_url="postgresql://test:test@db.invalid/test?sslmode=require")
    with tempfile.TemporaryDirectory(prefix="lumalab-memory-") as directory:
        path = Path(directory, "normalized.png")
        with Image.effect_noise((6000, 4000), 50).convert("RGB") as image:
            image.save(path, "PNG")
        started = perf_counter()
        output = render(path, Adjustments(brightness=115, contrast=120, saturation=130,
                                         warmth=27, sharpness=50, vignette=70), settings, preview=False)
        print(json.dumps({"megapixels": 24, "export_seconds": round(perf_counter() - started, 3),
                          "jpeg_bytes": len(output), "peak_rss_mib": round(peak_rss_bytes() / 1024**2, 1)}))


if __name__ == "__main__":
    main()
