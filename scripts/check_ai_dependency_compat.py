"""Guard against CrewAI/OpenAI dependency drift and runtime import breakage."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path


def _read_locked_versions(lock_path: Path) -> dict[str, str]:
    versions: dict[str, str] = {}
    for line in lock_path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if raw == "" or raw.startswith("#") or raw.startswith("-e "):
            continue
        if "==" not in raw:
            continue
        name, version = raw.split("==", maxsplit=1)
        key = name.strip().lower()
        versions[key] = version.strip()
    return versions


def main() -> int:
    project_root = Path(__file__).resolve().parent.parent
    lock_path = project_root / "requirements.lock"
    locked = _read_locked_versions(lock_path)

    for package in ("crewai", "openai"):
        if package not in locked:
            raise SystemExit(f"{package} is not pinned in requirements.lock")

    crewai = import_module("crewai")
    openai = import_module("openai")
    installed = {
        "crewai": str(getattr(crewai, "__version__", "")),
        "openai": str(getattr(openai, "__version__", "")),
    }

    mismatches = [
        f"{pkg}: installed={installed[pkg]} lock={locked[pkg]}"
        for pkg in ("crewai", "openai")
        if installed[pkg] != locked[pkg]
    ]
    if mismatches:
        raise SystemExit("Dependency drift detected: " + "; ".join(mismatches))

    try:
        import_module("crewai.llms.providers.openai.completion")
    except Exception as exc:  # pragma: no cover - runtime probe
        raise SystemExit(f"CrewAI/OpenAI compatibility check failed: {type(exc).__name__}: {exc}") from exc

    print("AI dependency compatibility check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
