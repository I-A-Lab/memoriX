#!/usr/bin/env python3
"""
Titan External Memory for LLM Agent - v1

Titan-inspired prototype:
- facts are atomized into small memory units;
- each fact is encoded into key/value vectors;
- a neural MLP memory learns key -> value at test time;
- retrieval combines neural score + lexical/entity/property safeguards;
- Ollama/Gemma generates the final answer from retrieved facts.

This is not the full Google Titans architecture trained end-to-end.
"""

from __future__ import annotations

import argparse, hashlib, re, shutil, time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple, Literal

import torch
import torch.nn as nn
import torch.nn.functional as F

# ---------------------------------------------------------------------------
# Embedded Titans-style Long-Term Memory
# ---------------------------------------------------------------------------
# Kept in this file on purpose so the Titan model remains self-contained, like
# the other model files in Test_models/models/. This is the memory-only part
# inspired by Aedelon/titans-pytorch-mlx, not a full Titans LLM.

ActivationName = Literal["silu", "gelu", "relu"]


@dataclass
class TitansMemoryConfig:
    """Configuration for the standalone Titans long-term memory module."""

    dim: int = 128
    num_memory_layers: int = 2
    memory_hidden_mult: float = 2.0
    memory_lr: float = 0.05
    memory_momentum: float = 0.90
    memory_decay: float = 0.001
    activation: ActivationName = "gelu"
    init_std: float = 0.02

    def __post_init__(self) -> None:
        if self.dim <= 0:
            raise ValueError("dim must be positive")
        if self.num_memory_layers < 1:
            raise ValueError("num_memory_layers must be >= 1")
        if not 0.0 < self.memory_lr <= 1.0:
            raise ValueError("memory_lr must be in (0, 1]")
        if not 0.0 <= self.memory_momentum < 1.0:
            raise ValueError("memory_momentum must be in [0, 1)")
        if not 0.0 <= self.memory_decay < 1.0:
            raise ValueError("memory_decay must be in [0, 1)")

    @property
    def memory_hidden_dim(self) -> int:
        return max(self.dim, int(self.dim * self.memory_hidden_mult))


def get_activation(name: ActivationName) -> nn.Module:
    if name == "silu":
        return nn.SiLU()
    if name == "gelu":
        return nn.GELU()
    if name == "relu":
        return nn.ReLU()
    raise ValueError(f"Unknown activation: {name}")


@dataclass
class MemoryState:
    """External state of the neural memory.

    weights represent M_t in the Titans paper.
    momentum represents S_t, the accumulated surprise.
    """

    weights: list[torch.Tensor]
    momentum: list[torch.Tensor]

    def detach(self) -> "MemoryState":
        return MemoryState(
            weights=[w.detach().clone() for w in self.weights],
            momentum=[m.detach().clone() for m in self.momentum],
        )

    def clone(self) -> "MemoryState":
        return MemoryState(
            weights=[w.clone() for w in self.weights],
            momentum=[m.clone() for m in self.momentum],
        )


class MemoryMLP(nn.Module):
    """The neural memory M.

    A 1-layer memory is equivalent to a linear associative memory.
    A 2+ layer memory is closer to the deep memory module discussed in Titans.
    """

    def __init__(self, config: TitansMemoryConfig) -> None:
        super().__init__()
        self.config = config
        self.layers = nn.ModuleList()

        if config.num_memory_layers == 1:
            self.layers.append(nn.Linear(config.dim, config.dim, bias=False))
        else:
            self.layers.append(nn.Linear(config.dim, config.memory_hidden_dim, bias=False))
            for _ in range(config.num_memory_layers - 2):
                self.layers.append(
                    nn.Linear(config.memory_hidden_dim, config.memory_hidden_dim, bias=False)
                )
            self.layers.append(nn.Linear(config.memory_hidden_dim, config.dim, bias=False))

        self.activation = get_activation(config.activation)
        self.reset_parameters()

    def reset_parameters(self) -> None:
        for layer in self.layers:
            nn.init.normal_(layer.weight, mean=0.0, std=self.config.init_std)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = x
        for idx, layer in enumerate(self.layers):
            h = layer(h)
            if idx < len(self.layers) - 1:
                h = self.activation(h)
        return h

    def get_weights(self) -> list[torch.Tensor]:
        return [layer.weight.detach().clone() for layer in self.layers]

    def set_weights(self, weights: list[torch.Tensor]) -> None:
        if len(weights) != len(self.layers):
            raise ValueError(
                f"Expected {len(self.layers)} weight tensors, got {len(weights)}"
            )
        with torch.no_grad():
            for layer, weight in zip(self.layers, weights, strict=True):
                layer.weight.copy_(weight.to(layer.weight.device, dtype=layer.weight.dtype))

    def associative_loss(self, keys: torch.Tensor, values: torch.Tensor) -> torch.Tensor:
        return F.mse_loss(self.forward(keys), values, reduction="mean")


class NeuralLongTermMemory(nn.Module):
    """Standalone Titans-style Neural Long-Term Memory.

    It performs retrieval using the current state, then optionally updates the
    memory weights using the associative loss:

        loss = || M(k_t) - v_t ||²

    The update follows the Titans intuition:

        S_t = eta * S_{t-1} - theta * grad(loss)
        M_t = (1 - alpha) * M_{t-1} + S_t

    where alpha is forgetting/decay, eta is surprise momentum, and theta is the
    test-time memory learning rate.
    """

    def __init__(self, config: TitansMemoryConfig | None = None) -> None:
        super().__init__()
        self.config = config or TitansMemoryConfig()
        dim = self.config.dim

        self.proj_k = nn.Linear(dim, dim, bias=False)
        self.proj_v = nn.Linear(dim, dim, bias=False)
        self.proj_q = nn.Linear(dim, dim, bias=False)
        self.proj_out = nn.Linear(dim, dim, bias=False)
        self.memory = MemoryMLP(self.config)

        self.reset_parameters()

        # The projections are part of the memory interface, not trained at test time here.
        for module in (self.proj_k, self.proj_v, self.proj_q, self.proj_out):
            for param in module.parameters():
                param.requires_grad_(False)

    def reset_parameters(self) -> None:
        for module in (self.proj_k, self.proj_v, self.proj_q, self.proj_out):
            nn.init.eye_(module.weight)

    def init_state(self, device: torch.device | str = "cpu") -> MemoryState:
        device = torch.device(device)
        weights = [w.detach().clone().to(device) for w in self.memory.get_weights()]
        momentum = [torch.zeros_like(w, device=device) for w in weights]
        return MemoryState(weights=weights, momentum=momentum)

    def project_keys_values_queries(
        self, x: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        keys = F.normalize(F.silu(self.proj_k(x)), p=2, dim=-1)
        values = F.normalize(F.silu(self.proj_v(x)), p=2, dim=-1)
        queries = F.normalize(F.silu(self.proj_q(x)), p=2, dim=-1)
        return keys, values, queries

    def retrieve(self, queries: torch.Tensor, state: MemoryState) -> torch.Tensor:
        self.memory.set_weights(state.weights)
        _, _, projected_queries = self.project_keys_values_queries(queries)
        retrieved = self.memory(projected_queries)
        return self.proj_out(retrieved)

    def forward(
        self,
        x: torch.Tensor,
        state: MemoryState | None = None,
        update: bool = True,
    ) -> tuple[torch.Tensor, MemoryState]:
        if x.ndim != 3:
            raise ValueError("x must have shape (batch, sequence, dim)")
        if x.shape[-1] != self.config.dim:
            raise ValueError(f"Expected last dim {self.config.dim}, got {x.shape[-1]}")

        if state is None:
            state = self.init_state(x.device)

        self.memory.set_weights(state.weights)
        keys, values, queries = self.project_keys_values_queries(x)

        # Read before write: M*_{t-1}(q_t)
        retrieved = self.memory(queries)
        output = self.proj_out(retrieved)

        if not update:
            return output, state.detach()

        grads = self._compute_gradients(keys, values)
        new_state = self._update_state(state, grads)
        return output, new_state.detach()

    def _compute_gradients(
        self, keys: torch.Tensor, values: torch.Tensor
    ) -> list[torch.Tensor]:
        for param in self.memory.parameters():
            param.requires_grad_(True)

        loss = self.memory.associative_loss(keys.detach(), values.detach())
        grads = torch.autograd.grad(
            loss,
            list(self.memory.parameters()),
            create_graph=False,
            allow_unused=True,
        )

        out: list[torch.Tensor] = []
        for grad, param in zip(grads, self.memory.parameters(), strict=True):
            out.append(torch.zeros_like(param) if grad is None else grad.detach())
            param.requires_grad_(False)
        return out

    def _update_state(self, state: MemoryState, grads: list[torch.Tensor]) -> MemoryState:
        alpha = self.config.memory_decay
        eta = self.config.memory_momentum
        theta = self.config.memory_lr

        new_weights: list[torch.Tensor] = []
        new_momentum: list[torch.Tensor] = []

        for weight, momentum, grad in zip(
            state.weights, state.momentum, grads, strict=True
        ):
            grad = grad.to(weight.device, dtype=weight.dtype)
            surprise = eta * momentum - theta * grad
            updated_weight = (1.0 - alpha) * weight + surprise
            new_momentum.append(surprise)
            new_weights.append(updated_weight)

        return MemoryState(weights=new_weights, momentum=new_momentum)

    @staticmethod
    def _as_sequence(x: torch.Tensor, dim: int, name: str) -> torch.Tensor:
        """Accept either (seq, dim) or (batch, seq, dim) tensors."""
        if x.ndim == 2:
            x = x.unsqueeze(0)
        if x.ndim != 3:
            raise ValueError(f"{name} must have shape (seq, dim) or (batch, seq, dim)")
        if x.shape[-1] != dim:
            raise ValueError(f"Expected {name} last dim {dim}, got {x.shape[-1]}")
        return x

    def _compute_gradients_from_projected(
        self, keys: torch.Tensor, values: torch.Tensor
    ) -> list[torch.Tensor]:
        """Gradient of ||M(keys) - values||² for already prepared pairs."""
        for param in self.memory.parameters():
            param.requires_grad_(True)

        loss = self.memory.associative_loss(keys.detach(), values.detach())
        grads = torch.autograd.grad(
            loss,
            list(self.memory.parameters()),
            create_graph=False,
            allow_unused=True,
        )

        out: list[torch.Tensor] = []
        for grad, param in zip(grads, self.memory.parameters(), strict=True):
            out.append(torch.zeros_like(param) if grad is None else grad.detach())
            param.requires_grad_(False)
        return out

    def consolidate(
        self,
        keys: torch.Tensor,
        values: torch.Tensor | None = None,
        state: MemoryState | None = None,
        *,
        steps: int = 3,
        reset_state: bool = False,
        keep_momentum: bool = False,
    ) -> MemoryState:
        """Replay explicit key/value associations into the long-term memory.

        This is the memory-only equivalent of the legacy Titan ``consolidate``
        method. Instead of asking a language model to summarize text, it replays
        the selected memory associations into the Titans LTM state.

        Parameters
        ----------
        keys:
            Tensor of memory keys, shape ``(seq, dim)`` or ``(batch, seq, dim)``.
        values:
            Tensor of target values with the same shape. If omitted, the method
            performs self-association ``M(key) -> key`` for compatibility.
        state:
            Previous LTM state. If omitted, a fresh state is created.
        steps:
            Number of replay passes. Small values, typically 2-5, are enough.
        reset_state:
            If True, rebuild the LTM from scratch using only the replayed pairs.
            This is useful after forgetting, because inactive facts are not
            replayed and therefore do not remain reinforced in long-term state.
        keep_momentum:
            If False, momentum is reset before consolidation for a cleaner
            offline replay phase.
        """
        if steps < 1:
            raise ValueError("steps must be >= 1")

        keys = self._as_sequence(keys, self.config.dim, "keys")
        if values is None:
            values = keys
        else:
            values = self._as_sequence(values, self.config.dim, "values")
            if values.shape != keys.shape:
                raise ValueError("values must have the same shape as keys")

        device = keys.device
        if state is None or reset_state:
            state = self.init_state(device)
        else:
            state = state.clone()

        if not keep_momentum:
            state = MemoryState(
                weights=[w.detach().clone().to(device) for w in state.weights],
                momentum=[torch.zeros_like(m, device=device) for m in state.momentum],
            )

        # Use the same normalization family as the online forward path, while
        # allowing external key/value pairs from TitanExternalMemory.
        projected_keys = F.normalize(F.silu(keys.to(device)), p=2, dim=-1)
        projected_values = F.normalize(F.silu(values.to(device)), p=2, dim=-1)

        for _ in range(steps):
            self.memory.set_weights(state.weights)
            grads = self._compute_gradients_from_projected(projected_keys, projected_values)
            state = self._update_state(state, grads).detach()

        return state.detach()

    def associative_loss_for_pairs(
        self, keys: torch.Tensor, values: torch.Tensor, state: MemoryState | None = None
    ) -> float:
        """Measure ||M(k) - v||² for explicit pairs without updating memory."""
        keys = self._as_sequence(keys, self.config.dim, "keys")
        values = self._as_sequence(values, self.config.dim, "values")
        if values.shape != keys.shape:
            raise ValueError("values must have the same shape as keys")
        if state is None:
            state = self.init_state(keys.device)
        self.memory.set_weights(state.weights)
        projected_keys = F.normalize(F.silu(keys), p=2, dim=-1)
        projected_values = F.normalize(F.silu(values), p=2, dim=-1)
        with torch.no_grad():
            loss = self.memory.associative_loss(projected_keys, projected_values)
        return float(loss.item())

    def associative_loss_for_input(
        self, x: torch.Tensor, state: MemoryState | None = None
    ) -> float:
        if state is None:
            state = self.init_state(x.device)
        self.memory.set_weights(state.weights)
        keys, values, _ = self.project_keys_values_queries(x)
        with torch.no_grad():
            loss = self.memory.associative_loss(keys, values)
        return float(loss.item())

    def count_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters())


# ---------------------------------------------------------------------------
# Titan external memory agent
# ---------------------------------------------------------------------------

USE_COLOR = True


class Ansi:
    RESET="\033[0m"; BOLD="\033[1m"; CYAN="\033[36m"; GREEN="\033[32m"
    YELLOW="\033[33m"; RED="\033[31m"; BLUE="\033[34m"; MAGENTA="\033[35m"


def color(text: str, code: str="") -> str:
    return f"{code}{text}{Ansi.RESET}" if USE_COLOR and code else text


def terminal_width(default: int=100) -> int:
    try: return min(max(shutil.get_terminal_size((default, 20)).columns, 72), 120)
    except Exception: return default


def wrap_text(text: str, width: int) -> List[str]:
    if not text: return [""]
    out=[]
    for raw in str(text).splitlines():
        cur=""
        for w in raw.split(" "):
            if not cur: cur=w
            elif len(cur)+1+len(w)<=width: cur += " " + w
            else: out.append(cur); cur=w
        out.append(cur)
    return out or [""]


def box(title: str, body: str="", code: str="") -> None:
    width=terminal_width(); inner=width-4; label=f" {title} "
    print(color("┌"+label+"─"*max(0, inner-len(label)+2)+"┐", code))
    for line in wrap_text(body, inner):
        print(color("│ ", code)+line.ljust(inner)+color(" │", code))
    print(color("└"+"─"*(width-2)+"┘", code))


def warn(text: str) -> None: print(color(f"⚠ {text}", Ansi.YELLOW))
def error(text: str) -> None: print(color(f"✗ {text}", Ansi.RED))
def info(text: str) -> None: print(color(f"• {text}", Ansi.BLUE))
def assistant_print(text: str) -> None: print(); box("ASSISTANT", text, Ansi.CYAN)
def memory_print(text: str) -> None: print(); box("TITAN MEMORY", text, Ansi.GREEN)
def system_print(text: str) -> None: print(); box("SYSTEM", text, Ansi.BLUE)


def truncate(text: str, n: int=120) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text)<=n else text[:n-3]+"..."


STOPWORDS = {
    "a","an","the","and","or","of","to","in","on","for","with","from","is","are","am",
    "was","were","be","been","being","as","i","me","my","mine","you","your","he","she",
    "it","they","we","his","her","their","this","that","these","those","do","does","did",
    "what","where","when","who","why","how","which","tell","give","show","more","about",
    "please","can","could","would","should","now","currently","actually","learn","remember","that",
    "ignore","random","noise","again"
}
QUESTION_STARTERS = ("what","where","when","who","why","how","which","do","does","did","can","could","would","should","is","are","am","tell me","explain","give me","show me")
MEMORY_MARKERS = ("my name is","i am","i'm","i live","i study","i work","i like","i love","my favorite","my favourite","i prefer","i want","i need","i was born","remember that","note that","save this","learn that","lives in","likes","favorite color","favourite color","favorite programming language","programming language","secret code","temporary access code","student id","office room","portfolio password","research group","operating system","was born","is from","works on","studies","is currently","wants to")
UPDATE_MARKERS = ("actually","now","changed","instead","no longer","correction","update:","is now","currently")
FORGET_MARKERS = ("forget","delete","remove","do not remember","don't remember","erase")
BROAD_MEMORY_PATTERNS = ("what do you know about me","what do you remember about me","summarize my profile","summarise my profile","who am i")

PROPERTY_PATTERNS: List[Tuple[str,str]] = [
    ("secret_code", r"\bsecret code\b|\brelease secret code\b|\btemporary access code\b|\baccess code\b"),
    ("backend_language", r"\bpreferred backend language\b|\bbackend language\b"),
    ("documentation_style", r"\bdocumentation style\b"),
    ("student_id", r"\bstudent id\b|\bid number\b"),
    ("office_room", r"\boffice room\b|\broom\b"),
    ("password", r"\bpassword\b"),
    ("research_group", r"\bresearch group\b|\blab\b|\blaboratory\b"),
    ("favorite_color", r"\bfavo[u]?rite color\b|\bcolor\b|\bcolour\b"),
    ("favorite_food", r"\bfavo[u]?rite food\b|\bfood\b"),
    ("favorite_language", r"\bfavo[u]?rite programming language\b|\bprogramming language\b|\bfavo[u]?rite language\b"),
    ("languages", r"\bspeaks?\b|\bwhich languages?\b|\bspoken languages?\b|\blanguages spoken\b"),
    ("favorite_os", r"\bfavo[u]?rite operating system\b|\boperating system\b|\bos\b"),
    ("favorite_opening", r"\bfavo[u]?rite chess opening\b|\bchess opening\b"),
    ("study", r"\bstud(?:y|ies|ying)\b|\bstudent\b|\bschool\b|\buniversity\b"),
    ("testing_framework", r"\btesting framework\b|\bunit tests?\b|\bpytest\b"),
    ("project", r"\bproject\b|\bworking on\b|\bworks on\b|\bbuild(?:ing)?\b|\bcreate\b"),
    ("work", r"\bwork[s]?\b|\bjob\b|\bengineer\b"),
    ("current_location", r"\bcurrently\b|\bcurrent location\b|\bwhere .* currently\b"),
    ("location", r"\blive[s]?\b|\blives in\b|\bwhere .* live\b|\bfrom\b"),
    ("age", r"\bage\b|\byears old\b"),
    ("name", r"\bname\b"),
]
SINGLE_VALUE_PROPERTIES = {"secret_code","student_id","office_room","password","research_group","favorite_color","favorite_food","favorite_language","favorite_os","favorite_opening","location","current_location","age","name","backend_language","documentation_style"}


def now() -> float: return time.time()
def fmt_time(ts: float) -> str: return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))
def clean_text(text: str) -> str: return re.sub(r"\s+", " ", str(text)).strip()
def normalize_text(text: str) -> str: return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
def words(text: str) -> List[str]: return re.findall(r"[a-zA-Z0-9_À-ÖØ-öø-ÿ']+", text.lower())
def keywords(text: str) -> set[str]: return {w for w in words(text) if len(w)>=3 and w not in STOPWORDS}
def l2_normalize(x: torch.Tensor, eps: float=1e-12) -> torch.Tensor: return x / x.norm(p=2, dim=-1, keepdim=True).clamp_min(eps)


def lexical_overlap(query: str, memory_text: str) -> float:
    q=keywords(query)
    return 0.0 if not q else len(q & keywords(memory_text)) / len(q)


def extract_entities(text: str) -> set[str]:
    found=set()
    for m in re.finditer(r"\b[A-Z][a-zA-ZÀ-ÖØ-öø-ÿ']+(?:\s+[A-Z][a-zA-ZÀ-ÖØ-öø-ÿ']+){0,2}\b", text):
        for token in words(m.group(0)):
            if len(token)>=3 and token not in STOPWORDS: found.add(token)
    for m in re.finditer(r"\b([A-Z][a-zA-ZÀ-ÖØ-öø-ÿ']+)'s\b", text):
        token=m.group(1).lower()
        if len(token)>=3: found.add(token)
    return found


def entity_match_score(query: str, memory_text: str) -> float:
    q=extract_entities(query)
    return 0.0 if not q else len(q & extract_entities(memory_text)) / len(q)


def subject_entity_match_score(q_entities: set[str], subject: Optional[str]) -> float:
    """
    Compare the query entities with the stored canonical subject.
    Prevents retrieving a memory for another person with the same last name.
    """
    if not q_entities or not subject:
        return 0.0
    subject_tokens=set(subject.split())
    return 0.0 if not subject_tokens else len(q_entities & subject_tokens) / len(q_entities)


def property_key(text: str) -> Optional[str]:
    lower=text.lower()
    for key, pattern in PROPERTY_PATTERNS:
        if re.search(pattern, lower): return key
    return None


def global_single_value_subject(text: str, prop: Optional[str]) -> Optional[str]:
    """Return a stable pseudo-subject for global single-value facts.

    Some useful agent memories are not attached to a named person, for example:
    - "The preferred backend language is C++."
    - "The release secret code is CODE-3053."

    The previous update logic only deactivated old values when both subject and
    property were detected. These global facts had a property but no subject, so
    older values stayed active and could outrank the newest memory. We use a
    deterministic pseudo-subject to make updates safe without affecting named
    profiles.
    """
    if not prop or prop not in SINGLE_VALUE_PROPERTIES:
        return None
    lower = normalize_text(text)
    if prop == "backend_language" and "backend language" in lower:
        return "global:preferred_backend_language"
    if prop == "secret_code" and "release secret code" in lower:
        return "global:release_secret_code"
    if prop == "secret_code" and "temporary access code" in lower:
        return "global:temporary_access_code"
    if prop == "documentation_style" and "documentation style" in lower:
        return "global:documentation_style"
    return None


def properties_compatible(query_prop: Optional[str], item_prop: Optional[str]) -> bool:
    if not query_prop or not item_prop:
        return False
    if query_prop == item_prop:
        return True
    compatible_groups = [
        {"location", "current_location"},
    ]
    return any(query_prop in group and item_prop in group for group in compatible_groups)


def property_match_score(query: str, memory_text: str) -> float:
    q=property_key(query)
    m=property_key(memory_text)
    return 0.0 if not q else (1.0 if properties_compatible(q, m) else 0.0)


def subject_exact_match(q_entities: set[str], subject: Optional[str]) -> bool:
    if not q_entities or not subject:
        return False
    subject_tokens=set(subject.split())
    return bool(subject_tokens) and subject_tokens.issubset(q_entities)


def is_broad_memory_question(question: str) -> bool:
    return any(p in question.lower().strip() for p in BROAD_MEMORY_PATTERNS)


def normalize_statement_for_storage(text: str) -> str:
    s=clean_text(text)
    # Benchmark and chat adapters often use wrappers such as
    # "Please remember this information: <fact>". These wrappers must not be
    # stored as part of the fact, otherwise subject/property extraction fails and
    # old values are not deactivated correctly.
    s=re.sub(r"(?i)^please\s+remember\s+this\s+information\s*:\s*", "", s).strip()
    s=re.sub(r"(?i)^please\s+remember\s*:\s*", "", s).strip()
    s=re.sub(r"(?i)^remember\s+this\s+information\s*:\s*", "", s).strip()
    s=re.sub(r"(?i)^(learn|remember|note)\s+that\s+", "", s).strip()
    s=re.sub(r"(?i)^save\s+this\s*:\s*", "", s).strip()
    s=re.sub(r"(?i)^(actually|correction|update)\s*[:,]?\s*", "", s).strip()
    return s


def extract_subject(text: str) -> Optional[str]:
    s=normalize_statement_for_storage(text); low=s.lower()
    if low.startswith(("my ","i ","i'm","i am")): return "user"
    # Multi-word possessive: "Sarah Nguyen's ...", "PriyaAlpha Meyer's ..."
    m=re.match(r"^([A-Z][a-zA-ZÀ-ÖØ-öø-ÿ']+(?:\s+[A-Z][a-zA-ZÀ-ÖØ-öø-ÿ']+){0,2})'s\b", s)
    if m: return " ".join(words(m.group(1)))
    m=re.match(r"^([A-Z][a-zA-ZÀ-ÖØ-öø-ÿ']+(?:\s+[A-Z][a-zA-ZÀ-ÖØ-öø-ÿ']+){0,2})\s+(?:is|lives|likes|works|studies|has|wants|enjoys|speaks)\b", s)
    return " ".join(words(m.group(1))) if m else None


def has_update_marker(text: str) -> bool: return any(m in text.lower() for m in UPDATE_MARKERS)


def looks_like_memory_statement(text: str) -> bool:
    s=clean_text(text); low=s.lower()
    if not s or s.endswith("?"): return False
    if any(m in low for m in MEMORY_MARKERS): return True
    if re.match(r"^[A-Z][a-zA-ZÀ-ÖØ-öø-ÿ']+(?:\s+[A-Z][a-zA-ZÀ-ÖØ-öø-ÿ']+){0,2}\s+(?:is|lives|likes|works|studies|has|wants|enjoys|speaks)\b", s): return True
    if re.match(r"^[A-Z][a-zA-ZÀ-ÖØ-öø-ÿ']+'s\s+.+\s+(?:is|are|was|were)\b", s): return True
    return False


def subject_display(subject: Optional[str]) -> Optional[str]:
    if not subject: return None
    return "I" if subject=="user" else " ".join(p.capitalize() for p in subject.split())


def split_sentences(text: str) -> List[str]:
    cleaned=normalize_statement_for_storage(text).replace(";", ".")
    chunks=[c.strip() for c in re.split(r"(?<=[.!?])\s+", cleaned) if c.strip()]
    return chunks or ([cleaned] if cleaned else [])


def split_memory_units(text: str) -> List[str]:
    units=[]; current_display=None
    for raw in split_sentences(text):
        sentence=raw.strip().rstrip(".")
        if not sentence: continue
        if current_display:
            sentence=re.sub(r"(?i)^(he|she|they)\s+", f"{current_display} ", sentence)
            sentence=re.sub(r"(?i)^his\s+", f"{current_display}'s ", sentence)
            sentence=re.sub(r"(?i)^her\s+", f"{current_display}'s ", sentence)
            sentence=re.sub(r"(?i)^their\s+", f"{current_display}'s ", sentence)
        subj=extract_subject(sentence)
        if subj: current_display=subject_display(subj)
        display=current_display or subject_display(extract_subject(sentence))
        if display:
            m=re.match(rf"^({re.escape(display)})\s+is\s+(.+?)\s+from\s+(.+)$", sentence, flags=re.I)
            if m:
                desc=m.group(2).strip(" ,"); place=m.group(3).strip(" ,")
                if desc: units.append(f"{display} is {desc}.")
                if place: units.append(f"{display} is from {place}.")
                continue
            m=re.match(rf"^({re.escape(display)})\s+stud(?:ies|y|ying)\s+(.+?)\s+and\s+works?\s+on\s+(.+)$", sentence, flags=re.I)
            if m:
                study=m.group(2).strip(" ,"); project=m.group(3).strip(" ,")
                if study: units.append(f"{display} studies {study}.")
                if project: units.append(f"{display} works on {project}.")
                continue
        final=sentence.strip()
        if final:
            units.append(final if final.endswith(".") else final+".")
    seen=set(); out=[]
    for u in units:
        key=normalize_text(u)
        if key not in seen:
            seen.add(key); out.append(u)
    return out


def classify_user_message(message: str) -> str:
    text=clean_text(message); low=text.lower()
    if low in {"/exit","exit","quit","/quit"}: return "exit"
    if low.startswith("/"): return "command"
    if any(m in low for m in FORGET_MARKERS): return "forget"
    if low.endswith("?") or low.startswith(QUESTION_STARTERS): return "ask"
    return "store" if looks_like_memory_statement(normalize_statement_for_storage(text)) else "chat"


def hashed_text_vector(text: str, dim: int=128) -> torch.Tensor:
    vec=torch.zeros(dim, dtype=torch.float32)
    toks=keywords(text) or set(words(text))
    for tok in toks:
        d=hashlib.sha256(tok.encode("utf-8")).digest()
        for off in range(0, 12, 2):
            idx=int.from_bytes(d[off:off+2], "little") % dim
            vec[idx] += 1.0 if d[off] % 2 == 0 else -1.0
    return l2_normalize(vec)


class TitanMemoryNetwork(nn.Module):
    def __init__(self, d_model: int=128, hidden_dim: int=256):
        super().__init__()
        self.d_model=d_model
        self.proj_k=nn.Linear(d_model, d_model, bias=False)
        self.proj_v=nn.Linear(d_model, d_model, bias=False)
        self.proj_q=nn.Linear(d_model, d_model, bias=False)
        self.memory_mlp=nn.Sequential(nn.Linear(d_model, hidden_dim), nn.GELU(), nn.Linear(hidden_dim, d_model))
        self._init_eye(self.proj_k); self._init_eye(self.proj_v); self._init_eye(self.proj_q)
        for p in list(self.proj_k.parameters())+list(self.proj_v.parameters())+list(self.proj_q.parameters()):
            p.requires_grad=False

    @staticmethod
    def _init_eye(layer: nn.Linear) -> None:
        with torch.no_grad():
            layer.weight.zero_(); n=min(layer.weight.shape); layer.weight[:n,:n]=torch.eye(n)

    def key(self, x: torch.Tensor) -> torch.Tensor: return l2_normalize(self.proj_k(x))
    def value(self, x: torch.Tensor) -> torch.Tensor: return l2_normalize(self.proj_v(x))
    def query(self, x: torch.Tensor) -> torch.Tensor: return l2_normalize(self.proj_q(x))
    def retrieve_value(self, q: torch.Tensor) -> torch.Tensor: return l2_normalize(self.memory_mlp(q))
    def associative_loss(self, k: torch.Tensor, v: torch.Tensor) -> torch.Tensor: return F.mse_loss(self.memory_mlp(k), v)


@dataclass
class MemoryItem:
    id: int
    text: str
    key: torch.Tensor
    value: torch.Tensor
    subject: Optional[str]=None
    property: Optional[str]=None
    active: bool=True
    surprise: float=0.0
    created_at: float=field(default_factory=now)
    updated_at: float=field(default_factory=now)
    access_count: int=0
    last_accessed_at: Optional[float]=None
    deactivated_reason: Optional[str]=None

    def to_serializable(self) -> Dict[str, object]:
        return self.__dict__.copy()

    @staticmethod
    def from_serializable(data: Dict[str, object]) -> "MemoryItem":
        return MemoryItem(
            id=int(data["id"]), text=str(data["text"]),
            key=data["key"].float().cpu(), value=data["value"].float().cpu(), # type: ignore[union-attr]
            subject=data.get("subject"), property=data.get("property"), active=bool(data.get("active", True)),
            surprise=float(data.get("surprise", 0.0)), created_at=float(data.get("created_at", now())),
            updated_at=float(data.get("updated_at", now())), access_count=int(data.get("access_count", 0)),
            last_accessed_at=data.get("last_accessed_at"), deactivated_reason=data.get("deactivated_reason")
        )


class TitanExternalMemory:
    def __init__(self, memory_path: Optional[Path]=None, d_model: int=128, hidden_dim: int=256,
                 max_items: int=5000, device: str="cpu", learning_rate: float=0.01,
                 weight_decay: float=0.001, replay_items: int=8, use_aedelon_ltm: bool=True,
                 ltm_momentum: float=0.90) -> None:
        self.memory_path=memory_path; self.d_model=d_model; self.hidden_dim=hidden_dim
        self.max_items=max_items; self.device=device; self.learning_rate=learning_rate
        self.weight_decay=weight_decay; self.replay_items=replay_items
        self.use_aedelon_ltm=use_aedelon_ltm; self.ltm_momentum=ltm_momentum
        info(f"Loading Titan neural memory on {device}.")

        # Legacy MLP network is kept for backwards compatibility with older saved
        # memories and as a fallback if the standalone Titans LTM is disabled.
        self.network=TitanMemoryNetwork(d_model, hidden_dim).to(device)
        self.optimizer=torch.optim.AdamW(self.network.memory_mlp.parameters(), lr=learning_rate, weight_decay=weight_decay)

        # Aedelon/Titans-inspired long-term neural memory. This is the part that
        # matches Tony's instruction: use the memory only, not a full Titans LLM.
        self.ltm_config=TitansMemoryConfig(
            dim=d_model,
            num_memory_layers=2,
            memory_hidden_mult=max(1.0, hidden_dim / max(1, d_model)),
            memory_lr=min(max(float(learning_rate), 1e-4), 1.0),
            memory_momentum=ltm_momentum,
            memory_decay=min(max(float(weight_decay), 0.0), 0.99),
            activation="gelu",
        )
        self.ltm=NeuralLongTermMemory(self.ltm_config).to(device)
        self.ltm_state=self.ltm.init_state(device)

        self._items: List[MemoryItem]=[]; self._next_id=1
        self.last_consolidated_at: Optional[float]=None
        if self.memory_path and self.memory_path.exists():
            try: self.load(self.memory_path); memory_print(f"Loaded {len(self.active_items)} active memory item(s).")
            except Exception as exc: warn(f"Could not load existing memory file: {exc}")

    @property
    def items(self) -> List[MemoryItem]: return self._items
    @property
    def active_items(self) -> List[MemoryItem]: return [i for i in self._items if i.active]
    @property
    def inactive_items(self) -> List[MemoryItem]: return [i for i in self._items if not i.active]

    def encode(self, text: str) -> torch.Tensor: return hashed_text_vector(text, self.d_model).to(self.device)

    @torch.no_grad()
    def _make_key_value(self, text: str) -> Tuple[torch.Tensor, torch.Tensor]:
        x=self.encode(text).unsqueeze(0)
        return self.network.key(x)[0].detach().cpu(), self.network.value(x)[0].detach().cpu()

    def _surprise(self, key: torch.Tensor, value: torch.Tensor) -> float:
        with torch.no_grad():
            if self.use_aedelon_ltm:
                pred=self.ltm.retrieve(key.to(self.device).view(1,1,-1), self.ltm_state).view(-1).detach().cpu()
                return float(F.mse_loss(pred, value.cpu()).item())
            pred=self.network.retrieve_value(key.to(self.device).unsqueeze(0))
            return float(F.mse_loss(pred, value.to(self.device).unsqueeze(0)).item())

    def _train_association(self, key: torch.Tensor, value: torch.Tensor, surprise: float, base_steps: int=12) -> None:
        steps=base_steps + min(28, int(surprise*400))

        if self.use_aedelon_ltm:
            # Update the standalone Titans LTM state at test time with explicit
            # key/value associations. This is closer to Titans' associative
            # objective M(k) -> v than the previous self-association replay.
            replay_items=sorted(self.active_items, key=lambda i: i.updated_at, reverse=True)[:self.replay_items]
            replay_keys=[key] + [i.key for i in replay_items]
            replay_values=[value] + [i.value for i in replay_items]
            keys=torch.stack([k.to(self.device) for k in replay_keys], dim=0).view(1, len(replay_keys), self.d_model)
            values=torch.stack([v.to(self.device) for v in replay_values], dim=0).view(1, len(replay_values), self.d_model)
            ltm_steps = 1 + min(4, int(max(0.0, surprise) * 100))
            self.ltm_state = self.ltm.consolidate(keys, values, self.ltm_state, steps=max(1, ltm_steps), reset_state=False, keep_momentum=True)
            return

        pairs=[(key,value)] + [(i.key,i.value) for i in sorted(self.active_items, key=lambda i: i.updated_at, reverse=True)[:self.replay_items]]
        self.network.train()
        for _ in range(max(1, steps)):
            self.optimizer.zero_grad(set_to_none=True)
            losses=[self.network.associative_loss(k.to(self.device).unsqueeze(0), v.to(self.device).unsqueeze(0)) for k,v in pairs]
            loss=torch.stack(losses).mean(); loss.backward()
            nn.utils.clip_grad_norm_(self.network.memory_mlp.parameters(), max_norm=1.0)
            self.optimizer.step()

    def store(self, text: str) -> Tuple[str, MemoryItem, List[MemoryItem]]:
        raw=clean_text(text); update_intent=has_update_marker(raw); text=normalize_statement_for_storage(raw)
        if not text: raise ValueError("Cannot store an empty memory.")
        norm=normalize_text(text)
        for item in self.active_items:
            if normalize_text(item.text)==norm:
                item.updated_at=now(); return "duplicate_ignored", item, []
        subject=self._resolve_subject(extract_subject(text)); prop=property_key(text)
        if subject is None:
            subject=global_single_value_subject(text, prop)
        key,value=self._make_key_value(text); surprise=self._surprise(key,value)
        deactivated=[]
        if subject and prop and prop in SINGLE_VALUE_PROPERTIES:
            for item in self.active_items:
                if item.subject==subject and item.property==prop:
                    item.active=False; item.updated_at=now()
                    item.deactivated_reason = ("explicitly updated" if update_intent else "replaced") + f" by newer memory about {subject}/{prop}"
                    deactivated.append(item)
        self._train_association(key, value, surprise)
        item=MemoryItem(self._next_id, text, key, value, subject=subject, property=prop, surprise=surprise)
        self._next_id+=1; self._items.append(item); self._enforce_capacity()
        return "stored", item, deactivated

    def store_text(self, text: str) -> List[Tuple[str, MemoryItem, List[MemoryItem]]]:
        return [self.store(unit) for unit in split_memory_units(text)]

    def atomize_existing_memories(self) -> Tuple[int,int]:
        changed=created=0
        for item in list(self.active_items):
            units=split_memory_units(item.text)
            if len(units)<=1: continue
            item.active=False; item.deactivated_reason="reindexed into atomic facts"; item.updated_at=now(); changed+=1
            for u in units:
                action,_,_=self.store(u)
                if action=="stored": created+=1
        return changed, created

    def consolidate(
        self,
        max_items: Optional[int]=None,
        steps: int=3,
        reset_ltm: bool=True,
        include_inactive: bool=False,
    ) -> Dict[str, object]:
        """Consolidate explicit memories into the Titans long-term memory.

        The legacy Titan implementation had a ``consolidate`` method that
        compressed all textual facts into a single consolidated summary and then
        retrained the neural memory on it. For the new memory-only Titan, we keep
        explicit MemoryItem objects for interpretability and targeted forgetting,
        but we replay their key/value associations into the LTM.

        By default ``reset_ltm=True`` rebuilds the neural LTM from active memories
        only. This prevents forgotten/inactive facts from remaining reinforced in
        the long-term state while keeping the explicit active/inactive memory list
        unchanged.
        """
        source = self.items if include_inactive else self.active_items
        if not source:
            return {
                "consolidated": 0,
                "steps": steps,
                "reset_ltm": reset_ltm,
                "include_inactive": include_inactive,
                "message": "Memory consolidation skipped: no memory items to consolidate.",
            }

        # Replay most important facts first: frequently used, surprising and
        # recently updated facts are more likely to matter for future answers.
        selected=sorted(
            source,
            key=lambda i: (i.access_count, i.surprise, i.updated_at),
            reverse=True,
        )
        if max_items is not None:
            selected=selected[:max(1, int(max_items))]

        if self.use_aedelon_ltm:
            keys=torch.stack([i.key.to(self.device) for i in selected], dim=0).view(1, len(selected), self.d_model)
            values=torch.stack([i.value.to(self.device) for i in selected], dim=0).view(1, len(selected), self.d_model)
            before=self.ltm.associative_loss_for_pairs(keys, values, self.ltm_state)
            self.ltm_state=self.ltm.consolidate(keys, values, self.ltm_state, steps=max(1, steps), reset_state=reset_ltm, keep_momentum=False)
            after=self.ltm.associative_loss_for_pairs(keys, values, self.ltm_state)
        else:
            # Fallback for the older local MLP memory. Re-train on selected
            # explicit pairs without changing the active/inactive item list.
            before=0.0
            self.network.train()
            pairs=[(i.key, i.value) for i in selected]
            for _ in range(max(1, steps * 4)):
                self.optimizer.zero_grad(set_to_none=True)
                losses=[self.network.associative_loss(k.to(self.device).unsqueeze(0), v.to(self.device).unsqueeze(0)) for k,v in pairs]
                loss=torch.stack(losses).mean(); loss.backward()
                nn.utils.clip_grad_norm_(self.network.memory_mlp.parameters(), max_norm=1.0)
                self.optimizer.step()
            after=0.0

        self.last_consolidated_at=now()
        return {
            "consolidated": len(selected),
            "steps": steps,
            "reset_ltm": reset_ltm,
            "include_inactive": include_inactive,
            "loss_before": before,
            "loss_after": after,
            "message": f"Consolidated {len(selected)} memory item(s) into Titans LTM.",
        }

    def retrieve(self, query: str, k: int=5, min_score: float=0.12) -> List[Tuple[float,Dict[str,float],MemoryItem]]:
        active=self.active_items
        if not active: return []
        if is_broad_memory_question(query):
            return [(1.0, {"neural":1.0,"key":0.0,"lexical":0.0,"entity":0.0,"property":0.0,"recency":0.0}, i) for i in sorted(active, key=lambda i: i.updated_at, reverse=True)[:max(k,8)]]
        qkey,_=self._make_key_value(query); qents=extract_entities(query); qprop=property_key(query)
        with torch.no_grad():
            if self.use_aedelon_ltm:
                nread=self.ltm.retrieve(qkey.to(self.device).view(1,1,-1), self.ltm_state).view(-1).detach().cpu()
            else:
                nread=self.network.retrieve_value(qkey.to(self.device).unsqueeze(0))[0].detach().cpu()
        scored=[]; t=now()
        for item in active:
            key_score=float(torch.dot(l2_normalize(qkey), l2_normalize(item.key)).item())
            neural=float(torch.dot(l2_normalize(nread), l2_normalize(item.value)).item())
            lex=lexical_overlap(query, item.text)
            ent=max(entity_match_score(query, item.text), subject_entity_match_score(qents, item.subject))
            prop=1.0 if qprop and properties_compatible(qprop, item.property) else property_match_score(query, item.text)
            rec=1.0/(1.0+max(0.0,(t-item.updated_at)/3600.0))
            ent_pen=-0.25 if qents and ent==0.0 else 0.0
            prop_bonus=0.12 if qprop and prop>0 else 0.0
            hybrid=0.24*neural + 0.20*key_score + 0.25*lex + 0.22*ent + 0.09*prop + 0.03*rec + ent_pen + prop_bonus
            details={"neural":neural,"key":key_score,"lexical":lex,"entity":ent,"property":prop,"recency":rec}
            if qents and ent==0.0 and lex<0.34 and prop==0.0: continue
            # For precise single-value properties, partial identity matches are unsafe.
            # Example: do not retrieve another person's secret code just because they
            # share the same last name.
            if qents and qprop in SINGLE_VALUE_PROPERTIES and prop>0 and ent<1.0: continue
            if hybrid>=min_score: scored.append((hybrid, details, item))

        # If the query names a precise subject and property, prefer exact
        # subject/property matches before neural/lexical scores. This fixes cases
        # where a profile sentence about the same person outranks the exact fact
        # being requested, e.g. asking for Sarah Nguyen's color returns her age.
        if qents and qprop:
            exact_subject_property = [
                row for row in scored
                if subject_exact_match(qents, row[2].subject) and properties_compatible(qprop, row[2].property)
            ]
            if exact_subject_property:
                scored = exact_subject_property

        scored.sort(key=lambda row: row[0], reverse=True); results=scored[:max(1,min(k,len(scored)))]
        for _,_,item in results:
            item.access_count+=1; item.last_accessed_at=now()
        return results

    def search_forget_candidates(self, query: str, k: int=5) -> List[Tuple[float,Dict[str,float],MemoryItem]]:
        candidates=self.retrieve(query, k=max(k,8), min_score=-1.0); safe=[]
        for score,details,item in candidates:
            if details["lexical"]>=0.34 or (details["entity"]>0 and details["property"]>0) or details["neural"]>=0.72 or details["key"]>=0.72:
                safe.append((score,details,item))
        safe.sort(key=lambda r: r[0], reverse=True); return safe[:k]

    def deactivate_ids(self, ids: Iterable[int], reason: str="forgotten") -> List[MemoryItem]:
        ids=set(ids); out=[]
        for item in self._items:
            if item.id in ids and item.active:
                item.active=False; item.deactivated_reason=reason; item.updated_at=now(); out.append(item)
        return out

    def reset(self) -> None:
        self._items.clear(); self._next_id=1
        self.network=TitanMemoryNetwork(self.d_model, self.hidden_dim).to(self.device)
        self.optimizer=torch.optim.AdamW(self.network.memory_mlp.parameters(), lr=self.learning_rate, weight_decay=self.weight_decay)
        self.ltm=NeuralLongTermMemory(self.ltm_config).to(self.device)
        self.ltm_state=self.ltm.init_state(self.device)

    def stats(self) -> Dict[str,object]:
        return {"active_items":len(self.active_items),"inactive_items":len(self.inactive_items),"total_items":len(self.items),"d_model":self.d_model,"hidden_dim":self.hidden_dim,"device":self.device,"memory_path":str(self.memory_path) if self.memory_path else None,"ltm_enabled":self.use_aedelon_ltm,"ltm_parameters":self.ltm.count_parameters() if self.use_aedelon_ltm else 0,"last_consolidated_at":fmt_time(self.last_consolidated_at) if self.last_consolidated_at else None}

    def save(self, path: Optional[Path]=None) -> None:
        target=path or self.memory_path
        if target is None: raise ValueError("No memory path configured.")
        target.parent.mkdir(parents=True, exist_ok=True)
        torch.save({"version":2,"next_id":self._next_id,"d_model":self.d_model,"hidden_dim":self.hidden_dim,"items":[i.to_serializable() for i in self._items],"network_state":self.network.state_dict(),"optimizer_state":self.optimizer.state_dict(),"ltm_enabled":self.use_aedelon_ltm,"ltm_config":self.ltm_config.__dict__,"last_consolidated_at":self.last_consolidated_at,"ltm_state":{"weights":[w.detach().cpu() for w in self.ltm_state.weights],"momentum":[m.detach().cpu() for m in self.ltm_state.momentum]}}, target)

    def load(self, path: Optional[Path]=None) -> None:
        target=path or self.memory_path
        if target is None: raise ValueError("No memory path configured.")
        payload=torch.load(target, map_location="cpu")
        self._items=[MemoryItem.from_serializable(x) for x in payload.get("items", [])]
        self._next_id=int(payload.get("next_id", len(self._items)+1))
        self.last_consolidated_at=payload.get("last_consolidated_at")
        if payload.get("network_state"):
            self.network.load_state_dict(payload["network_state"]); self.network.to(self.device)
        if payload.get("optimizer_state"): self.optimizer.load_state_dict(payload["optimizer_state"])
        if payload.get("ltm_state"):
            raw_state=payload["ltm_state"]
            self.ltm_state=MemoryState(
                weights=[w.to(self.device) for w in raw_state.get("weights", [])],
                momentum=[m.to(self.device) for m in raw_state.get("momentum", [])],
            )

    def _resolve_subject(self, subject: Optional[str]) -> Optional[str]:
        if not subject or subject=="user" or subject.startswith("global:"): return subject
        subjects=sorted({i.subject for i in self.active_items if i.subject and not i.subject.startswith("global:")})
        if subject in subjects: return subject
        # Do not collapse two different full names that share a first name.
        # The previous logic mapped "Sarah Martin" to existing "Sarah Nguyen"
        # when Sarah Nguyen was the only Sarah in memory, causing identity
        # collisions and deactivating the wrong memories. Only resolve ambiguous
        # short references such as "Sarah" to an existing full subject.
        if len(subject.split()) > 1:
            return subject
        first=subject.split()[0]; matches=[s for s in subjects if s and s.split()[0]==first]
        return matches[0] if len(matches)==1 else subject

    def _enforce_capacity(self) -> None:
        if len(self._items)<=self.max_items: return
        inactive=sorted(self.inactive_items, key=lambda i:i.updated_at)
        remove={i.id for i in inactive[:max(0,len(self._items)-self.max_items)]}
        self._items=[i for i in self._items if i.id not in remove]
        if len(self._items)>self.max_items:
            self._items.sort(key=lambda i:(i.active,i.updated_at), reverse=True)
            self._items=self._items[:self.max_items]


def ollama_chat(model: str, system: str, user: str) -> str:
    try:
        import ollama  # type: ignore
    except Exception as exc:
        raise RuntimeError("Failed to import `ollama`. Install with `pip install ollama` and ensure Ollama is running.") from exc
    resp=ollama.chat(model=model, messages=[{"role":"system","content":system},{"role":"user","content":user}])
    msg=resp.get("message", {}) if isinstance(resp, dict) else getattr(resp, "message", {})
    content=msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", None)
    return (content or "").strip()


def build_prompt(question: str, retrieved: List[Tuple[float,Dict[str,float],MemoryItem]], show_citations: bool=False) -> Tuple[str,str]:
    cite = "At the end, cite the memory id like [memory: id]." if show_citations else "Do not mention memory IDs or retrieval scores."
    system=("You are a helpful assistant connected to an external Titan-inspired neural memory.\n"
            "Use the provided MEMORY only when relevant.\n"
            "If the memory does not contain the answer, say: I do not know based on memory.\n"
            "If memories conflict, prefer active, recent, and specific memories.\n"
            "Do not invent personal facts.\n"+cite+"\nAnswer naturally and concisely.")
    if not retrieved: return system, f"Question: {question}\n\nMEMORY:\n(none)\n\nAnswer:"
    lines=[f"[{rank}] id={item.id}; score={score:.3f}; subject={item.subject}; property={item.property}; text={item.text}" for rank,(score,_,item) in enumerate(retrieved,1)]
    return system, f"Question: {question}\n\nMEMORY:\n"+"\n".join(lines)+"\n\nAnswer:"


def ask_with_memory(question: str, memory: TitanExternalMemory, ollama_model: str, topk: int, min_score: float, debug: bool, show_citations: bool) -> str:
    retrieved=memory.retrieve(question, k=topk, min_score=min_score)
    if debug:
        if retrieved:
            lines=[f"#{i.id} | score={s:.3f} | neural={d['neural']:.3f} key={d['key']:.3f} lex={d['lexical']:.3f} ent={d['entity']:.3f} prop={d['property']:.3f} | {i.text}" for s,d,i in retrieved]
            box("DEBUG RETRIEVED TITAN MEMORY", "\n".join(lines), Ansi.MAGENTA)
        else:
            box("DEBUG RETRIEVED TITAN MEMORY", "No relevant memory found.", Ansi.YELLOW)
    system,user=build_prompt(question, retrieved, show_citations)
    return ollama_chat(ollama_model, system, user) or "(no response)"


@dataclass
class RuntimeConfig:
    debug: bool=False
    show_citations: bool=False


def print_help() -> None:
    body=("Natural mode:\n"
          "  Lucas's secret code is 8392.                -> stored automatically\n"
          "  What is Lucas's secret code?                -> answered using Titan memory\n\n"
          "Commands:\n"
          "  /store <text>          Force storing a memory\n"
          "  /ask <question>        Force asking a question\n"
          "  /search <query>        Show retrieval results without asking Ollama\n"
          "  /forget <query>        Safely forget the best matching memory only\n"
          "  /forget --all <query>  Forget all safe matches after typing YES\n"
          "  /consolidate           Replay active memories into Titans LTM\n"
          "  /consolidate --keep    Consolidate without resetting LTM state\n"
          "  /memories              Show active memories\n"
          "  /memories all          Show active and inactive memories\n"
          "  /debug on | off        Show or hide retrieval details\n"
          "  /citations on | off    Show or hide memory IDs in final answers\n"
          "  /stats                 Show memory statistics\n"
          "  /save /load /reset /exit")
    box("HELP", body, Ansi.CYAN)


def print_memories(memory: TitanExternalMemory, include_inactive: bool=False, limit: int=80) -> None:
    items=memory.items if include_inactive else memory.active_items
    if not items: warn("No memory stored."); return
    lines=[]
    for item in sorted(items, key=lambda x:x.updated_at, reverse=True)[:limit]:
        status="active" if item.active else f"inactive ({item.deactivated_reason or 'no reason'})"
        lines.append(f"#{item.id} | {status} | subject={item.subject} | property={item.property} | surprise={item.surprise:.4f} | {item.text}")
    box("TITAN MEMORIES", "\n".join(lines), Ansi.CYAN)


def print_store_results(results: List[Tuple[str,MemoryItem,List[MemoryItem]]]) -> None:
    if not results: warn("Nothing was stored."); return
    lines=[]
    for action,item,deactivated in results:
        if action=="duplicate_ignored": lines.append(f"Already remembered: {truncate(item.text)}")
        elif deactivated:
            lines.append(f"Updated memory: {truncate(item.text)}")
            lines.append("Deactivated older related fact(s): "+", ".join(f"#{x.id}" for x in deactivated))
        else: lines.append(f"Saved: {truncate(item.text)} | surprise={item.surprise:.4f}")
    memory_print("\n".join(lines))


def print_search(memory: TitanExternalMemory, query: str, topk: int, min_score: float) -> None:
    res=memory.retrieve(query, k=topk, min_score=min_score)
    if not res: warn("No relevant memory found."); return
    lines=[f"#{i.id} | score={s:.3f} | neural={d['neural']:.3f} key={d['key']:.3f} lex={d['lexical']:.3f} ent={d['entity']:.3f} prop={d['property']:.3f} | {i.text}" for s,d,i in res]
    box("TITAN SEARCH RESULTS", "\n".join(lines), Ansi.MAGENTA)


def handle_forget(query: str, memory: TitanExternalMemory, forget_all: bool) -> None:
    query=clean_text(query)
    if not query: warn("Give a query to forget, for example: /forget Lucas secret code"); return
    candidates=memory.search_forget_candidates(query, k=8 if forget_all else 5)
    if not candidates: warn("No safe matching memory found. Nothing was deleted."); return
    lines=[f"#{i.id} | score={s:.3f} | neural={d['neural']:.3f} key={d['key']:.3f} lex={d['lexical']:.3f} ent={d['entity']:.3f} prop={d['property']:.3f} | {i.text}" for s,d,i in candidates]
    box("FORGET CANDIDATES", "\n".join(lines), Ansi.YELLOW)
    if forget_all:
        if input(color("Deactivate ALL these memories? Type YES to confirm: ", Ansi.RED)).strip()!="YES":
            warn("Cancelled. No memory was deactivated."); return
        ids=[i.id for _,_,i in candidates]
    else:
        best=candidates[0][2]
        if input(color(f"Deactivate only best match #{best.id}? [y/N]: ", Ansi.RED)).strip().lower() not in {"y","yes"}:
            warn("Cancelled. No memory was deactivated."); return
        ids=[best.id]
    changed=memory.deactivate_ids(ids, reason=f"forgotten by query: {query}")
    try: memory.save()
    except Exception: pass
    memory_print("Memory deactivated: "+", ".join(f"#{i.id}" for i in changed)) if changed else warn("Nothing was changed.")


def handle_command(line: str, memory: TitanExternalMemory, ollama_model: str, topk: int, min_score: float, runtime: RuntimeConfig) -> bool:
    lower=line.lower().strip()
    if lower in {"/exit","/quit"}: return False
    if lower=="/help": print_help(); return True
    if lower=="/debug on": runtime.debug=True; system_print("Debug mode enabled."); return True
    if lower=="/debug off": runtime.debug=False; system_print("Debug mode disabled."); return True
    if lower=="/citations on": runtime.show_citations=True; system_print("Citations enabled."); return True
    if lower=="/citations off": runtime.show_citations=False; system_print("Citations disabled."); return True
    if lower=="/stats": box("STATS", "\n".join(f"{k}: {v}" for k,v in memory.stats().items()), Ansi.CYAN); return True
    if lower=="/memories": print_memories(memory, False); return True
    if lower=="/memories all": print_memories(memory, True); return True
    if lower=="/reindex":
        changed,created=memory.atomize_existing_memories(); memory.save()
        memory_print(f"Reindexed broad memories.\nDeactivated broad items: {changed}\nCreated atomic facts: {created}"); return True
    if lower.startswith("/consolidate"):
        reset_ltm="--keep" not in lower
        result=memory.consolidate(steps=3, reset_ltm=reset_ltm, include_inactive=False)
        memory.save()
        body=(f"{result['message']}\n"
              f"reset_ltm={result['reset_ltm']} | steps={result['steps']}\n"
              f"loss_before={float(result.get('loss_before',0.0)):.6f} | loss_after={float(result.get('loss_after',0.0)):.6f}")
        memory_print(body); return True
    if lower=="/save": memory.save(); system_print("Titan memory saved."); return True
    if lower=="/load": memory.load(); system_print("Titan memory loaded."); return True
    if lower=="/reset":
        if input(color("Clear ALL Titan memories? Type YES to confirm: ", Ansi.RED)).strip()=="YES":
            memory.reset(); memory.save(); system_print("Titan memory reset.")
        else: warn("Reset cancelled.")
        return True
    if line.startswith("/store "):
        try: res=memory.store_text(line[len("/store "):].strip()); memory.save(); print_store_results(res)
        except Exception as exc: error(f"Could not store memory: {exc}")
        return True
    if line.startswith("/ask "):
        try: assistant_print(ask_with_memory(line[len("/ask "):].strip(), memory, ollama_model, topk, min_score, runtime.debug, runtime.show_citations))
        except Exception as exc: error(f"Ollama error: {exc}"); info(f"Make sure the model exists: ollama pull {ollama_model}")
        return True
    if line.startswith("/search "): print_search(memory, line[len("/search "):].strip(), topk, min_score); return True
    if line.startswith("/forget "):
        raw=line[len("/forget "):].strip(); forget_all=False
        if raw.startswith("--all "): forget_all=True; raw=raw[len("--all "):].strip()
        handle_forget(raw, memory, forget_all); return True
    warn("Unknown command. Type /help."); return True


def main(argv: Optional[List[str]]=None) -> int:
    base_dir=Path(__file__).resolve().parent
    parser=argparse.ArgumentParser(description="Titan external memory for LLM agent")
    parser.add_argument("--ollama-model", default="gemma2:2b")
    parser.add_argument("--topk", type=int, default=5)
    parser.add_argument("--min-score", type=float, default=0.12)
    parser.add_argument("--max-items", type=int, default=5000)
    parser.add_argument("--memory-file", default=str(base_dir/"titan_memory_store.pt"))
    parser.add_argument("--d-model", type=int, default=128)
    parser.add_argument("--hidden-dim", type=int, default=256)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--citations", action="store_true")
    parser.add_argument("--no-color", action="store_true")
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu", choices=["cpu","cuda"])
    args=parser.parse_args(argv)

    global USE_COLOR; USE_COLOR=not args.no_color
    runtime=RuntimeConfig(debug=args.debug, show_citations=args.citations)
    memory=TitanExternalMemory(memory_path=Path(args.memory_file), d_model=args.d_model, hidden_dim=args.hidden_dim, max_items=args.max_items, device=args.device)

    box("READY", "Titan natural chat mode is enabled.\nWrite normally to chat or teach the memory.\nUse /help for commands and /debug on to inspect retrieval.", Ansi.GREEN)

    while True:
        try: line=input(color("\nYou> ", Ansi.BOLD)).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            try: memory.save(); system_print("Titan memory saved. Bye.")
            except Exception: system_print("Bye.")
            return 0
        if not line: continue
        intent=classify_user_message(line)
        if intent=="exit":
            try: memory.save(); system_print("Titan memory saved. Bye.")
            except Exception as exc: warn(f"Could not save memory: {exc}")
            return 0
        if intent=="command":
            if not handle_command(line, memory, args.ollama_model, args.topk, args.min_score, runtime):
                try: memory.save(); system_print("Titan memory saved. Bye.")
                except Exception as exc: warn(f"Could not save memory: {exc}")
                return 0
            continue
        if intent=="store":
            try: res=memory.store_text(line); memory.save(); print_store_results(res)
            except Exception as exc: error(f"Could not store memory: {exc}")
            continue
        if intent=="forget":
            query=re.sub(r"(?i)\b(forget|delete|remove|erase|do not remember|don't remember)\b","",line).strip()
            handle_forget(query or line, memory, False); continue
        try: assistant_print(ask_with_memory(line, memory, args.ollama_model, args.topk, args.min_score, runtime.debug, runtime.show_citations))
        except Exception as exc: error(f"Ollama error: {exc}"); info(f"Make sure the model exists: ollama pull {args.ollama_model}")


if __name__ == "__main__":
    raise SystemExit(main())




class TitanModel:
    """Compatibility wrapper used by Test_models/main.py and benchmarks.

    The important fix is that storing a fact must not be treated as a question.
    Previous behavior stored the memory, then immediately asked Ollama to answer
    the storage sentence, which produced "I do not know based on memory" in the
    terminal even though the memory was correctly saved.
    """

    def __init__(self, model_name: str = "llama3.2:1b", max_capacity: int = 5000, config=None):
        # Optional compatibility with the previous Titan V2 test file.
        if config is not None:
            model_name = getattr(config, "ollama_model", model_name)
            max_capacity = getattr(config, "max_items", max_capacity)
            d_model = getattr(config, "d_model", 128)
            hidden_dim = getattr(config, "hidden_dim", 256)
            device = getattr(config, "device", "auto")
            learning_rate = getattr(config, "learning_rate", 0.01)
            weight_decay = getattr(config, "weight_decay", 0.001)
            replay_items = getattr(config, "replay_items", 8)
            if device == "auto":
                device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            d_model = 128
            hidden_dim = 256
            device = "cuda" if torch.cuda.is_available() else "cpu"
            learning_rate = 0.01
            weight_decay = 0.001
            replay_items = 8

        self.model_name = model_name
        self.max_capacity = max_capacity
        self.memory = TitanExternalMemory(
            memory_path=Path("memory_titan.pt"),
            d_model=d_model,
            hidden_dim=hidden_dim,
            max_items=max_capacity,
            device=device,
            learning_rate=learning_rate,
            weight_decay=weight_decay,
            replay_items=replay_items,
            use_aedelon_ltm=True,
        )
        self.history = []
        self._pending_response: Optional[str] = None
        self._last_query: Optional[str] = None
        self._set_system_prompt()

    def _set_system_prompt(self):
        system_prompt = (
            "You are a highly intelligent, concise, and helpful AI assistant. "
            "You always communicate in English. "
            "Your underlying architecture relies on a Titan neural memory."
        )
        self.history.append({"role": "system", "content": system_prompt})

    def get_active_tokens_count(self) -> int:
        return len(self.memory.active_items)

    def get_dropped_tokens_count(self) -> int:
        return len(self.memory.inactive_items)

    def get_memory_dump(self) -> str:
        active = self.memory.active_items
        lines = [f"[bold cyan]Architecture:[/bold cyan] [bold]Titan (Neural Memory + Aedelon LTM)[/bold]",
                 f"[bold yellow]Active Memories:[/bold yellow] {len(active)} / {self.max_capacity}",
                 f"[bold red]Inactive Memories:[/bold red] {len(self.memory.inactive_items)}",
                 f"[bold blue]LTM enabled:[/bold blue] {self.memory.use_aedelon_ltm}",
                 f"[bold blue]LTM parameters:[/bold blue] {self.memory.stats().get('ltm_parameters', 0)}",
                 ""]
        if active:
            lines.append("[bold green]Recent Active Memories:[/bold green]")
            for item in sorted(active, key=lambda x: x.updated_at, reverse=True)[:10]:
                lines.append(f"  • #{item.id} | Subj: {item.subject} | Prop: {item.property} | {item.text}")
        else:
            lines.append("No active memories.")
        return "\n".join(lines)

    def _format_store_response(self, results: List[Tuple[str, MemoryItem, List[MemoryItem]]]) -> str:
        if not results:
            return "Nothing was stored."
        lines = []
        for action, item, deactivated in results:
            if action == "duplicate_ignored":
                lines.append(f"Already remembered: {item.text}")
            elif deactivated:
                lines.append(f"Updated memory: {item.text}")
                lines.append("Deactivated older related memory/memories: " + ", ".join(f"#{x.id}" for x in deactivated))
            else:
                lines.append(f"Saved in Titan memory: {item.text}")
        return "\n".join(lines)

    def _format_search_response(self, query: str, k: int = 5, min_score: float = 0.0) -> str:
        results = self.memory.retrieve(query, k=k, min_score=min_score)
        if not results:
            return "No relevant memory found."
        lines = []
        for score, details, item in results:
            lines.append(
                f"#{item.id} | score={score:.3f} | subject={item.subject} | property={item.property} | {item.text}"
            )
        return "\n".join(lines)

    def _forget_non_interactive(self, query: str) -> str:
        candidates = self.memory.search_forget_candidates(query, k=5)
        if not candidates:
            return "No safe matching memory found. Nothing was forgotten."
        best = candidates[0][2]
        changed = self.memory.deactivate_ids([best.id], reason=f"forgotten by query: {query}")
        if changed:
            return "Forgotten/deactivated: " + ", ".join(f"#{i.id} {i.text}" for i in changed)
        return "Nothing was changed."

    def add_user_message(self, message: str):
        self.history.append({"role": "user", "content": message})
        self._pending_response = None
        self._last_query = message

        stripped = message.strip()
        lower = stripped.lower()

        # Commands used by the standalone Titan CLI. They now also work in main.py.
        if lower.startswith("/store "):
            results = self.memory.store_text(stripped[len("/store "):].strip())
            self._pending_response = self._format_store_response(results)
            return

        if lower.startswith("/ask "):
            self._last_query = stripped[len("/ask "):].strip()
            return

        if lower.startswith("/search "):
            query = stripped[len("/search "):].strip()
            self._pending_response = self._format_search_response(query, min_score=-1.0)
            return

        if lower.startswith("/forget "):
            query = stripped[len("/forget "):].strip()
            self._pending_response = self._forget_non_interactive(query)
            return

        if lower.startswith("/consolidate"):
            reset_ltm = "--keep" not in lower
            result = self.memory.consolidate(steps=3, reset_ltm=reset_ltm, include_inactive=False)
            self._pending_response = (
                f"{result['message']} "
                f"loss_before={float(result.get('loss_before', 0.0)):.6f}, "
                f"loss_after={float(result.get('loss_after', 0.0)):.6f}."
            )
            return

        # Benchmark/main adapters use this wrapper to teach facts. Treat it as
        # storage even if the wrapped fact itself is not recognized by the
        # heuristic marker list.
        for prefix in (
            "please remember this information:",
            "remember this information:",
            "please remember:",
        ):
            if lower.startswith(prefix):
                fact = stripped[len(prefix):].strip()
                results = self.memory.store_text(fact)
                self._pending_response = self._format_store_response(results)
                return

        intent = classify_user_message(message)
        if intent == "store":
            results = self.memory.store_text(message)
            self._pending_response = self._format_store_response(results)
        elif intent == "forget":
            query = re.sub(r"(?i)\b(forget|delete|remove|erase|do not remember|don't remember)\b", "", message).strip()
            self._pending_response = self._forget_non_interactive(query or message)

    def add_assistant_message(self, message: str):
        self.history.append({"role": "assistant", "content": message})

    def _direct_memory_answer(self, question: str, retrieved: List[Tuple[float, Dict[str, float], MemoryItem]]) -> Optional[str]:
        """Return a deterministic answer when memory retrieval is unambiguous.

        This prevents a very small local LLM such as llama3.2:1b from ignoring the
        MEMORY block and saying it does not know although the right memory was
        retrieved. The answer still comes from the memory item, not from a hardcoded
        benchmark rule.
        """
        if not retrieved:
            return None
        best_score, details, best = retrieved[0]
        qprop = property_key(question)
        qents = extract_entities(question)
        strong_match = best_score >= 0.45 or (qprop and best.property == qprop and details.get("entity", 0.0) >= 1.0)
        if strong_match:
            return f"Based on memory: {best.text}"
        return None

    def generate_response_stream(self):
        if self._pending_response is not None:
            yield self._pending_response
            self._pending_response = None
            return

        last_user_message = self._last_query or self.history[-1]['content']
        retrieved = self.memory.retrieve(last_user_message, k=5, min_score=0.12)

        direct = self._direct_memory_answer(last_user_message, retrieved)
        if direct is not None:
            yield direct
            return

        system, user = build_prompt(last_user_message, retrieved, show_citations=False)
        inference_messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ]

        try:
            import ollama
            response = ollama.chat(
                model=self.model_name,
                messages=inference_messages,
                stream=True,
            )
            full = ""
            for chunk in response:
                if 'message' in chunk and 'content' in chunk['message']:
                    piece = chunk['message']['content']
                    full += piece
                    yield piece
            # Note: direct fallback is intentionally done before streaming to avoid
            # printing wrong tokens and then correcting them afterwards.
        except Exception as e:
            yield f"\n[Error communicating with Ollama: {str(e)}]"

    def save_memory(self, filepath: str = "memory_titan.pt"):
        self.memory.memory_path = Path(filepath)
        self.memory.save()
        import pickle
        history_path = filepath + "_history.pkl"
        with open(history_path, 'wb') as f:
            pickle.dump(self.history, f)

    def load_memory(self, filepath: str = "memory_titan.pt") -> bool:
        self.memory.memory_path = Path(filepath)
        if not self.memory.memory_path.exists():
            return False
        try:
            self.memory.load()
            import pickle, os
            history_path = filepath + "_history.pkl"
            if os.path.exists(history_path):
                with open(history_path, 'rb') as f:
                    self.history = pickle.load(f)
            return True
        except Exception:
            return False

    def clear_memory(self):
        self.history = []
        self._pending_response = None
        self._last_query = None
        self._set_system_prompt()
        self.memory.reset()
