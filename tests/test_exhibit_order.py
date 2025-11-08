"""
Tests for the exhibit order randomization service.

Tests the functions that manage randomized exhibit navigation:
- Random order generation
- Navigation helpers (next/previous/by-index)
- Total exhibit count
"""

import pytest
from unittest.mock import patch

from app.services.exhibit_order import (
    generate_random_exhibit_order,
    get_exhibit_slug_by_index,
    get_exhibit_index_by_slug,
    get_total_exhibits,
    get_next_exhibit_slug,
    get_previous_exhibit_slug,
)


# ============================================================================
# Random Order Generation Tests
# ============================================================================


@patch("app.services.exhibit_order.get_yaml_slugs")
def test_generate_random_exhibit_order(mock_get_yaml_slugs):
    """Test that random order generation returns all slugs in random order."""
    mock_slugs = ["zongler", "bludicka", "dva", "ptak"]
    mock_get_yaml_slugs.return_value = mock_slugs.copy()

    order = generate_random_exhibit_order()

    # Should contain all slugs
    assert len(order) == len(mock_slugs)
    assert set(order) == set(mock_slugs)


# ============================================================================
# Navigation Helper Tests
# ============================================================================


def test_get_exhibit_slug_by_index():
    """Test getting exhibit by index."""
    order = ["zongler", "bludicka", "dva", "ptak"]

    assert get_exhibit_slug_by_index(order, 0) == "zongler"
    assert get_exhibit_slug_by_index(order, 1) == "bludicka"
    assert get_exhibit_slug_by_index(order, 3) == "ptak"


def test_get_exhibit_slug_by_index_out_of_bounds():
    """Test getting exhibit with invalid index."""
    order = ["zongler", "bludicka", "dva"]

    assert get_exhibit_slug_by_index(order, -1) is None
    assert get_exhibit_slug_by_index(order, 3) is None
    assert get_exhibit_slug_by_index(order, 100) is None


def test_get_exhibit_index_by_slug():
    """Test finding index of a slug."""
    order = ["zongler", "bludicka", "dva", "ptak"]

    assert get_exhibit_index_by_slug(order, "zongler") == 0
    assert get_exhibit_index_by_slug(order, "dva") == 2
    assert get_exhibit_index_by_slug(order, "ptak") == 3


def test_get_exhibit_index_by_slug_not_found():
    """Test finding index of non-existent slug."""
    order = ["zongler", "bludicka", "dva"]

    assert get_exhibit_index_by_slug(order, "nonexistent") is None


def test_get_total_exhibits():
    """Test getting total exhibit count."""
    order = ["zongler", "bludicka", "dva", "ptak"]
    assert get_total_exhibits(order) == 4

    empty_order = []
    assert get_total_exhibits(empty_order) == 0


def test_get_next_exhibit_slug():
    """Test getting next exhibit slug."""
    order = ["zongler", "bludicka", "dva", "ptak"]

    assert get_next_exhibit_slug(order, "zongler") == "bludicka"
    assert get_next_exhibit_slug(order, "bludicka") == "dva"
    assert get_next_exhibit_slug(order, "dva") == "ptak"


def test_get_next_exhibit_slug_last():
    """Test getting next exhibit when at last position."""
    order = ["zongler", "bludicka", "dva", "ptak"]

    # Last exhibit has no next
    assert get_next_exhibit_slug(order, "ptak") is None


def test_get_next_exhibit_slug_not_found():
    """Test getting next exhibit for non-existent slug."""
    order = ["zongler", "bludicka", "dva"]

    assert get_next_exhibit_slug(order, "nonexistent") is None


def test_get_previous_exhibit_slug():
    """Test getting previous exhibit slug."""
    order = ["zongler", "bludicka", "dva", "ptak"]

    assert get_previous_exhibit_slug(order, "ptak") == "dva"
    assert get_previous_exhibit_slug(order, "dva") == "bludicka"
    assert get_previous_exhibit_slug(order, "bludicka") == "zongler"


def test_get_previous_exhibit_slug_first():
    """Test getting previous exhibit when at first position."""
    order = ["zongler", "bludicka", "dva", "ptak"]

    # First exhibit has no previous
    assert get_previous_exhibit_slug(order, "zongler") is None


def test_get_previous_exhibit_slug_not_found():
    """Test getting previous exhibit for non-existent slug."""
    order = ["zongler", "bludicka", "dva"]

    assert get_previous_exhibit_slug(order, "nonexistent") is None


# ============================================================================
# Edge Cases
# ============================================================================


def test_empty_order():
    """Test all functions with empty order list."""
    empty_order = []

    assert get_total_exhibits(empty_order) == 0
    assert get_exhibit_slug_by_index(empty_order, 0) is None
    assert get_exhibit_index_by_slug(empty_order, "any") is None
    assert get_next_exhibit_slug(empty_order, "any") is None
    assert get_previous_exhibit_slug(empty_order, "any") is None


def test_single_exhibit_order():
    """Test navigation with single exhibit."""
    single_order = ["zongler"]

    assert get_total_exhibits(single_order) == 1
    assert get_exhibit_slug_by_index(single_order, 0) == "zongler"
    assert get_exhibit_index_by_slug(single_order, "zongler") == 0

    # Single exhibit has no next/previous
    assert get_next_exhibit_slug(single_order, "zongler") is None
    assert get_previous_exhibit_slug(single_order, "zongler") is None
