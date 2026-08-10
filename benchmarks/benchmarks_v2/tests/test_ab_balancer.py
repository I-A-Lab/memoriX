from __future__ import annotations

import pytest

from benchmarks.orchestrator.ab_balancer import determine_order, verify_balance


class TestDetermineOrderOddSeed:
    def test_determine_order_odd_seed(self):
        """Odd seed returns (no_memory, memorix_core) for pair 0."""
        order = determine_order(seed=3, pair_index=0)
        assert order == ("no_memory", "memorix_core")

    def test_determine_order_odd_seed_other(self):
        """Another odd seed confirms same ordering."""
        order = determine_order(seed=7, pair_index=0)
        assert order == ("no_memory", "memorix_core")


class TestDetermineOrderEvenSeed:
    def test_determine_order_even_seed(self):
        """Even seed returns (memorix_core, no_memory) for pair 0."""
        order = determine_order(seed=4, pair_index=0)
        assert order == ("memorix_core", "no_memory")

    def test_determine_order_even_seed_zero(self):
        """Zero (even) seed returns (memorix_core, no_memory) for pair 0."""
        order = determine_order(seed=0, pair_index=0)
        assert order == ("memorix_core", "no_memory")


class TestDetermineOrderAlternates:
    def test_determine_order_alternates(self):
        """Orders alternate correctly across pair indices."""
        seed = 42
        order_0 = determine_order(seed=seed, pair_index=0)
        order_1 = determine_order(seed=seed, pair_index=1)
        order_2 = determine_order(seed=seed, pair_index=2)

        assert order_0 == order_2
        assert order_0 != order_1

    def test_determine_order_alternates_odd_seed(self):
        """Alternation works for odd seeds too."""
        seed = 33
        order_0 = determine_order(seed=seed, pair_index=0)
        order_1 = determine_order(seed=seed, pair_index=1)

        assert order_0 != order_1
        assert order_0 == ("no_memory", "memorix_core")


class TestVerifyBalanceCorrect:
    def test_verify_balance_correct(self):
        """Correctly balanced orders pass verification."""
        orders = []
        for i in range(4):
            orders.append(determine_order(seed=42, pair_index=i))

        assert verify_balance(orders) is True

    def test_verify_balance_small_set(self):
        """Balanced 2-element set passes."""
        order_a = determine_order(seed=0, pair_index=0)
        order_b = determine_order(seed=0, pair_index=1)
        assert verify_balance([order_a, order_b]) is True


class TestVerifyBalanceIncorrect:
    def test_verify_balance_incorrect(self):
        """Incorrectly balanced orders fail verification."""
        bad_orders = [
            ("no_memory", "memorix_core"),
            ("no_memory", "memorix_core"),
            ("no_memory", "memorix_core"),
            ("no_memory", "memorix_core"),
        ]
        assert verify_balance(bad_orders) is False

    def test_verify_balance_empty(self):
        """Empty list considered balanced (vacuously true)."""
        assert verify_balance([]) is True
