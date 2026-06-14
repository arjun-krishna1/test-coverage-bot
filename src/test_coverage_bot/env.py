from __future__ import annotations

import os
from pathlib import Path


class DotEnvLoader:
    def load(self, path: Path) -> None:
        if not path.exists():
            return

        for line in path.read_text().splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            os.environ.setdefault(key, value.strip().strip('"').strip("'"))
