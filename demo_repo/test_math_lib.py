"""Unit tests for math_lib demonstrating CI/CD test suite failures."""

import pytest
from math_lib import calculate_discounted_average, compute_tax


def test_standard_discounted_average():
    # Regular valid inputs
    result = calculate_discounted_average([10.0, 20.0, 30.0], discount=0.1)
    assert result == 18.0


def test_single_item():
    result = calculate_discounted_average([100.0], discount=0.25)
    assert result == 75.0


def test_empty_prices_edge_case():
    # Will fail with ZeroDivisionError in original code
    result = calculate_discounted_average([])
    assert result == 0.0


def test_all_negative_prices_filtered():
    # Will fail with ZeroDivisionError because all elements get filtered out
    result = calculate_discounted_average([-10.0, -25.0])
    assert result == 0.0


def test_tax_computation():
    assert compute_tax(100.0, 0.08) == 8.0
    assert compute_tax(-50.0) == 0.0
