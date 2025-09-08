import yaml
from pathlib import Path
from typing import Dict, Any


def load_site_copy(content_dir: str = "content") -> Dict[str, Any]:
    """Load site-level copy from content/site_copy.yml.

    Returns a nested dict with keys like 'header', 'footer', 'index', 'thanks'.
    If file is missing or invalid, returns an empty dict.
    """
    p = Path(content_dir) / "site_copy.yml"
    if not p.exists():
        return {}
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        return data
    except Exception:
        return {}
