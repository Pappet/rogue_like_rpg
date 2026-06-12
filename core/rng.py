"""Deterministic seed derivation for run-scoped randomness.

A single world seed fans out into independent, stable sub-seeds — one per
subsystem or map — via ``derive_seed(world_seed, label)``. The derivation
uses CRC32 of the label (stable across processes and Python versions,
unlike ``hash()``), so the same world seed always reproduces the same
world regardless of generation order.
"""

import zlib


def derive_seed(base_seed: int, label: str) -> int:
    """Derive a stable sub-seed from a base seed and a string label."""
    return (base_seed ^ zlib.crc32(label.encode("utf-8"))) & 0x7FFFFFFF
