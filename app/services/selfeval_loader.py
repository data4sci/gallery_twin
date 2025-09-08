import yaml
from pathlib import Path

SELFEVAL_PATH = "content/selfeval.yml"


class SelfEvalConfig:
    _data = None

    @classmethod
    def load(cls):
        path = Path(SELFEVAL_PATH)
        if not path.exists():
            cls._data = {}
            return
        cls._data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    @classmethod
    def get_questions(cls, lang: str = "en"):
        if cls._data is None:
            cls.load()
        # English-only: prefer 'en' section, fall back to top-level 'questions'
        if cls._data.get("en"):
            return cls._data.get("en", {}).get("questions", [])
        return cls._data.get("questions", [])


# Načti při startu aplikace
SelfEvalConfig.load()
