"""
Exhibition feedback configuration loader.
"""

import yaml
from pathlib import Path
from typing import Dict, List, Any


class ExhibitionFeedbackConfig:
    """Configuration loader for exhibition feedback questions."""

    @staticmethod
    def get_questions() -> List[Dict[str, Any]]:
        """Load exhibition feedback questions from YAML file."""
        config_path = Path("content/exhibition_feedback.yml")

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                return config.get("questions", [])
        except FileNotFoundError:
            # Fallback questions if file doesn't exist
            return [
                {
                    "id": "exhibition_rating",
                    "type": "likert",
                    "text": "Jak se vám výstava líbila?",
                    "options": {"min": 1, "max": 5},
                    "required": True,
                },
                {
                    "id": "ai_art_opinion",
                    "type": "text",
                    "text": "Co si myslíte o AI v umění?",
                    "required": False,
                },
            ]
        except Exception:
            return []
