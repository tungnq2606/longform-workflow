"""Output languages: config/languages.json, shared by every project."""
import json
import os
from dataclasses import dataclass
from typing import Optional

from tools.longform import paths


@dataclass
class Lang:
    code: str
    name: str
    voice_engine: str
    voice: str
    speed: float
    font: str
    line_break: str
    chars_per_second: float = 15.0  # Plan 6 voice parts
    max_part_seconds: Optional[float] = None
    max_part_chars: Optional[int] = None


def load_languages():
    with open(os.path.join(paths.config(), "languages.json"), encoding="utf-8") as f:
        data = json.load(f)
    return {code: Lang(code=code, **v) for code, v in data["languages"].items()}
