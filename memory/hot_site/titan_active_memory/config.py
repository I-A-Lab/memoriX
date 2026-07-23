"""
Titan memory configuration for memoriX.

Titan is the active long-term memory layer.

Important:
- the default backend is now titan_external, not the JSONL adapter;
- d_model=256 and hidden_dim=256 are used for the active neural memory;
- 256^3 = 16,777,216 target values;
- this does not mean loading 16 million text memories directly in RAM;
- hot/cold sync keeps the active Titan memory bounded while the cold site
  persists durable metadata, archives and future vector/graph/document stores.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


TITAN_MEMORY_ROOT = Path("memory") / "hot_site" / "titan_active_memory"
TITAN_MEMORY_DATA_DIR = TITAN_MEMORY_ROOT / "data"

DEFAULT_TITAN_MEMORY_PATH = TITAN_MEMORY_DATA_DIR / "long_term_memory.jsonl"
DEFAULT_TITAN_NEURAL_PATH = TITAN_MEMORY_DATA_DIR / "titan_memory.pt"
DEFAULT_TITAN_METADATA_PATH = TITAN_MEMORY_DATA_DIR / "titan_metadata.jsonl"

DEFAULT_TITAN_DIM = 256
DEFAULT_TITAN_TARGET_VALUES = DEFAULT_TITAN_DIM ** 3

VALID_TITAN_BACKENDS = {
    "jsonl_adapter",
    "titan_external",
}


def get_env_int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def get_env_path(name: str, default: Path) -> Path:
    value = os.getenv(name)
    return Path(value) if value else default


def get_titan_backend(default: str = "titan_external") -> str:
    backend = os.getenv("MEMORIX_TITAN_BACKEND", default).strip()

    if backend not in VALID_TITAN_BACKENDS:
        raise ValueError(
            f"Invalid MEMORIX_TITAN_BACKEND={backend!r}. "
            f"Expected one of: {sorted(VALID_TITAN_BACKENDS)}"
        )

    return backend


def get_titan_device(default: str = "cpu") -> str:
    return os.getenv("MEMORIX_TITAN_DEVICE", default).strip()


@dataclass
class TitanMemoryConfig:
    storage_path: Path = DEFAULT_TITAN_MEMORY_PATH
    neural_path: Path = DEFAULT_TITAN_NEURAL_PATH
    metadata_path: Path = DEFAULT_TITAN_METADATA_PATH

    backend: str = "titan_external"
    device: str = "cpu"

    d_model: int = DEFAULT_TITAN_DIM
    hidden_dim: int = DEFAULT_TITAN_DIM
    target_dim: int = DEFAULT_TITAN_DIM
    target_values: int = DEFAULT_TITAN_TARGET_VALUES

    top_k: int = 5

    # Hot site = active RAM memory.
    max_hot_items: int = 50_000

    # Cold site = durable disk storage.
    max_cold_items: int = DEFAULT_TITAN_TARGET_VALUES

    # This is the max_items passed to Titan active memory.
    # It should not be 6 million by default, otherwise RAM can explode.
    max_items: int = 50_000


def load_titan_memory_config() -> TitanMemoryConfig:
    target_dim = get_env_int("MEMORIX_TITAN_TARGET_DIM", DEFAULT_TITAN_DIM)

    return TitanMemoryConfig(
        storage_path=get_env_path("MEMORIX_TITAN_JSONL_PATH", DEFAULT_TITAN_MEMORY_PATH),
        neural_path=get_env_path("MEMORIX_TITAN_NEURAL_PATH", DEFAULT_TITAN_NEURAL_PATH),
        metadata_path=get_env_path("MEMORIX_TITAN_METADATA_PATH", DEFAULT_TITAN_METADATA_PATH),
        backend=get_titan_backend(),
        device=get_titan_device(),
        d_model=get_env_int("MEMORIX_TITAN_D_MODEL", target_dim),
        hidden_dim=get_env_int("MEMORIX_TITAN_HIDDEN_DIM", target_dim),
        target_dim=target_dim,
        target_values=get_env_int(
            "MEMORIX_TITAN_TARGET_VALUES",
            target_dim ** 3,
        ),
        top_k=get_env_int("MEMORIX_TITAN_TOP_K", 5),
        max_hot_items=get_env_int("MEMORIX_MAX_HOT_ITEMS", 50_000),
        max_cold_items=get_env_int("MEMORIX_MAX_COLD_ITEMS", DEFAULT_TITAN_TARGET_VALUES),
        max_items=get_env_int("MEMORIX_TITAN_MAX_ITEMS", 50_000),
    )
