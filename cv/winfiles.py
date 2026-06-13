"""Windows-safe file helpers (WinError 32 retries)."""
import os
import shutil
import time


def _retry(fn, attempts: int = 8, delay: float = 0.25) -> None:
    last: BaseException | None = None
    for i in range(attempts):
        try:
            fn()
            return
        except (PermissionError, OSError) as e:
            last = e
            if getattr(e, "winerror", None) != 32 and not isinstance(e, PermissionError):
                raise
            if i < attempts - 1:
                time.sleep(delay * (i + 1))
    if last is not None:
        raise last


def safe_unlink(path: str) -> None:
    if not os.path.exists(path):
        return

    def _do() -> None:
        os.remove(path)

    _retry(_do)


def safe_replace(src: str, dst: str) -> None:
    def _do() -> None:
        os.replace(src, dst)

    _retry(_do)


def safe_rmtree(path: str) -> None:
    if not os.path.isdir(path):
        return

    def _do() -> None:
        shutil.rmtree(path)

    _retry(_do)
