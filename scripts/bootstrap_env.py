from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SAFE_PIP_VERSION = "25.1.1"

def _install_requirements(project_root: Path) -> None:
    pip = Path(sys.prefix) / "bin" / "pip"
    subprocess.run([str(pip), "install", f"pip=={SAFE_PIP_VERSION}"], check=True)
    for req in ("requirements.txt", "requirements-dev.txt"):
        subprocess.run([str(pip), "install", "-r", str(project_root / req)], check=True)


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    venv_path = project_root / ".venv"
    if Path(sys.prefix).resolve() != venv_path.resolve():
        if not venv_path.exists():
            subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)
        subprocess.run([str(venv_path / "bin" / "python"), str(Path(__file__).resolve())], check=True)
        return
    _install_requirements(project_root)
    print("[bootstrap] environment configured.")


if __name__ == "__main__":
    main()
