from __future__ import annotations

from typing import List, Tuple


def determine_order(seed: int, pair_index: int) -> Tuple[str, str]:
    """Determine the order for a given seed and pair index.

    Even seeds: (memorix_core, no_memory) for pair 0, alternates.
    Odd seeds: (no_memory, memorix_core) for pair 0, alternates.
    """
    seed_parity = seed % 2
    pair_parity = pair_index % 2

    # XOR the two parities: 0 means memorix_core first, 1 means no_memory first
    if (seed_parity ^ pair_parity) == 0:
        return ("memorix_core", "no_memory")
    return ("no_memory", "memorix_core")


def verify_balance(orders: List[Tuple[str, str]]) -> bool:
    """Verify that memorix_core and no_memory appear equally often as the first variant."""
    mc_first = sum(1 for first, _ in orders if first == "memorix_core")
    nm_first = sum(1 for first, _ in orders if first == "no_memory")
    total = len(orders)

    if total == 0:
        return True

    # Allow at most 1 unit of imbalance for odd counts
    return abs(mc_first - nm_first) <= 1


def generate_orders(
    seeds: List[int], pairs_count: int
) -> List[Tuple[int, int, str, str]]:
    """Generate the full order list for all seed/pair combinations.

    Returns list of (seed, pair_index, first, second) tuples.
    """
    orders: List[Tuple[int, int, str, str]] = []
    for seed in seeds:
        for pair_idx in range(pairs_count):
            first, second = determine_order(seed, pair_idx)
            orders.append((seed, pair_idx, first, second))
    return orders
