"""
Service for managing randomized exhibit order for each session.

Each visitor gets exhibits in a unique random order, stored in their session.
"""

import random
from typing import List

from app.services.content_loader import get_yaml_slugs


def generate_random_exhibit_order() -> List[str]:
    """
    Generate a randomized list of all exhibit slugs.

    Returns:
        List of exhibit slugs in random order, e.g. ["zongler", "bludicka", "dva", ...]
    """
    # Get all exhibit slugs from YAML files
    slugs = get_yaml_slugs("content/exhibits")

    # Shuffle the list in place
    random.shuffle(slugs)

    return slugs


def get_exhibit_slug_by_index(exhibit_order: List[str], index: int) -> str | None:
    """
    Get exhibit slug at a specific index in the randomized order.

    Args:
        exhibit_order: List of slugs in randomized order
        index: Index to retrieve (0-based)

    Returns:
        Exhibit slug at that index, or None if index out of bounds
    """
    if 0 <= index < len(exhibit_order):
        return exhibit_order[index]
    return None


def get_exhibit_index_by_slug(exhibit_order: List[str], slug: str) -> int | None:
    """
    Find the index of a specific exhibit slug in the randomized order.

    Args:
        exhibit_order: List of slugs in randomized order
        slug: Slug to find

    Returns:
        Index of the slug, or None if not found
    """
    try:
        return exhibit_order.index(slug)
    except ValueError:
        return None


def get_total_exhibits(exhibit_order: List[str]) -> int:
    """Get total number of exhibits."""
    return len(exhibit_order)


def get_next_exhibit_slug(exhibit_order: List[str], current_slug: str) -> str | None:
    """
    Get the next exhibit slug after the current one.

    Args:
        exhibit_order: List of slugs in randomized order
        current_slug: Current exhibit slug

    Returns:
        Next exhibit slug, or None if current is last or not found
    """
    current_index = get_exhibit_index_by_slug(exhibit_order, current_slug)
    if current_index is None:
        return None

    return get_exhibit_slug_by_index(exhibit_order, current_index + 1)


def get_previous_exhibit_slug(exhibit_order: List[str], current_slug: str) -> str | None:
    """
    Get the previous exhibit slug before the current one.

    Args:
        exhibit_order: List of slugs in randomized order
        current_slug: Current exhibit slug

    Returns:
        Previous exhibit slug, or None if current is first or not found
    """
    current_index = get_exhibit_index_by_slug(exhibit_order, current_slug)
    if current_index is None or current_index == 0:
        return None

    return get_exhibit_slug_by_index(exhibit_order, current_index - 1)
