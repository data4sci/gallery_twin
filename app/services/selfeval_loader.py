import yaml
from pathlib import Path

SELFEVAL_PATH = "content/selfeval.yml"


class SelfEvalConfig:
    _questions = None

    @classmethod
    def load(cls):
        path = Path(SELFEVAL_PATH)
        if not path.exists():
            cls._questions = []
            return
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        cls._questions = data.get("questions", [])

    @classmethod
    def get_questions(cls):
        if cls._questions is None:
            cls.load()
        return cls._questions


# Načti při startu aplikace
SelfEvalConfig.load()
