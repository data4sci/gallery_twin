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
    def get_questions(cls, lang: str = "cz"):
        if cls._data is None:
            cls.load()
        return cls._data.get(lang, {}).get("questions", [])


# Načti při startu aplikace
SelfEvalConfig.load()
