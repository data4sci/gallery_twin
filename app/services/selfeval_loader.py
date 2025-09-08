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
        # Support both flattened top-level format and nested 'en' section.
        if cls._data.get("questions"):
            return cls._data.get("questions", [])
        if cls._data.get("en"):
            return cls._data.get("en", {}).get("questions", [])
        return []

    @classmethod
    def get_meta(cls, lang: str = "en"):
        """Return metadata for the selfeval page (title, lead, continue_button).

        The YAML keeps these under the language key (e.g., en.title).
        """
        if cls._data is None:
            cls.load()
        # Support top-level meta keys first, then nested 'en' section
        if (
            cls._data.get("title")
            or cls._data.get("lead")
            or cls._data.get("continue_button")
        ):
            return {
                "title": cls._data.get("title"),
                "lead": cls._data.get("lead"),
                "continue_button": cls._data.get("continue_button"),
            }
        if cls._data.get("en"):
            meta = cls._data.get("en", {})
            return {
                "title": meta.get("title"),
                "lead": meta.get("lead"),
                "continue_button": meta.get("continue_button"),
            }
        return {"title": None, "lead": None, "continue_button": None}


# Načti při startu aplikace
SelfEvalConfig.load()
