"""Output languages: config/languages.json, shared by every project."""
import json
import os
from dataclasses import dataclass

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


def load_languages():
    with open(os.path.join(paths.config(), "languages.json"), encoding="utf-8") as f:
        data = json.load(f)
    return {code: Lang(code=code, **v) for code, v in data["languages"].items()}
