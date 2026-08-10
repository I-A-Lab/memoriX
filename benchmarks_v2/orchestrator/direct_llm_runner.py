"""Direct LLM runner for benchmarking without OpenCode CLI.

This module uses LLM backends directly to generate code solutions,
then evaluates them against expected outputs. This enables benchmarking
with free/local models (Ollama, HuggingFace) without API costs.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import random
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from .llm_backends.base import LLMBackend, LLMResponse
from .real_runner_adapter import FAMILY_TO_KIND


@dataclass(frozen=True, slots=True)
class DirectRunRequest:
    """Request to execute a direct LLM benchmark run."""
    family_id: str
    seed: int
    mode: str  # "no_memory" | "memorix_core"
    backend: LLMBackend
    timeout_seconds: int = 120
    distractor_count: int = 50
    top_k: int = 10


@dataclass(frozen=True, slots=True)
class DirectRunResult:
    """Result of a direct LLM benchmark run."""
    family_id: str
    seed: int
    mode: str
    passed: bool
    exit_code: int
    timed_out: bool
    duration_ms: float
    case_count: int
    passed_case_count: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    solution_sha256: str
    generated_code_preview: str
    error: Optional[str] = None


def _build_prompt(
    family_id: str,
    seed: int,
    mode: str,
    distractor_count: int = 50,
) -> tuple[str, dict[str, Any], str]:
    """Build the prompt, expected output, and scaffold for a task.
    
    Returns (prompt, expected, scaffold).
    """
    kind = FAMILY_TO_KIND.get(family_id)
    if kind is None:
        raise ValueError(f"Unknown family_id: {family_id}")
    
    rng = random.Random(f"{seed}|{kind}|40.7")
    
    # Generate task parameters based on kind
    if kind == "csv_delimiter":
        delimiter = rng.choice([";", "|", "\t"])
        expected = {"delimiter": delimiter}
        decision = f"Use delimiter {delimiter!r} for CSV serialization."
        scaffold = (
            "from __future__ import annotations\n\n"
            "def serialize_rows(rows: list[list[object]]) -> str:\n"
            "    raise NotImplementedError\n"
        )
        behavior = (
            "Implement serialize_rows(rows). Convert every cell with str(), join cells "
            f"using delimiter {delimiter!r}, join rows with one LF, no trailing LF."
        )
    elif kind == "username_separator":
        separator = rng.choice(["-", "_", "."])
        expected = {"separator": separator}
        decision = f"Use separator {separator!r} for username normalization."
        scaffold = (
            "from __future__ import annotations\n\n"
            "def normalize_username(value: str) -> str:\n"
            "    raise NotImplementedError\n"
        )
        behavior = (
            "Implement normalize_username(value). Trim and lowercase, replace "
            f"whitespace with {separator!r}, collapse repeated separators."
        )
    elif kind == "retry_schedule":
        base = rng.choice([0.1, 0.25, 0.5])
        factor = rng.choice([1.5, 2.0, 3.0])
        expected = {"base": base, "factor": factor}
        decision = f"Retry starts at {base}s, multiplied by {factor}."
        scaffold = (
            "from __future__ import annotations\n\n"
            "def retry_delays(attempts: int) -> list[float]:\n"
            "    raise NotImplementedError\n"
        )
        behavior = (
            f"Implement retry_delays(attempts). Return empty list for attempts <= 0. "
            f"Initial delay {base}, multiply by {factor} each attempt, round to 3 decimals."
        )
    elif kind == "date_format":
        fmt = rng.choice(["%d/%m/%Y", "%Y-%m-%d", "%m.%d.%Y"])
        expected = {"format": fmt}
        decision = f"Use date format {fmt!r}."
        scaffold = (
            "from __future__ import annotations\n"
            "from datetime import date\n\n"
            "def format_date(value: date) -> str:\n"
            "    raise NotImplementedError\n"
        )
        behavior = f"Implement format_date(value) using strftime format {fmt!r}."
    elif kind == "cache_key":
        separator = rng.choice(["::", ":", "|"])
        expected = {"separator": separator}
        decision = f"Cache keys use separator {separator!r}."
        scaffold = (
            "from __future__ import annotations\n\n"
            "def build_cache_key(namespace: str, identifier: str) -> str:\n"
            "    raise NotImplementedError\n"
        )
        behavior = (
            f"Implement build_cache_key(namespace, identifier). Trim both, lowercase "
            f"namespace, join with {separator!r}."
        )
    elif kind == "page_size":
        default = rng.choice([20, 25, 30])
        maximum = rng.choice([80, 100, 120])
        expected = {"default": default, "maximum": maximum}
        decision = f"Default page size {default}, max {maximum}."
        scaffold = (
            "from __future__ import annotations\n\n"
            "def normalize_page_size(requested: int | None) -> int:\n"
            "    raise NotImplementedError\n"
        )
        behavior = (
            f"Implement normalize_page_size(requested). Default {default} when None, "
            f"clamp to 1..{maximum}."
        )
    elif kind == "boolean_tokens":
        variants = [("true", "yes", "1"), ("enabled", "on", "yes"), ("active", "true", "y")]
        tokens = rng.choice(variants)
        expected = {"true_tokens": list(tokens)}
        decision = f"True tokens: {list(tokens)}."
        scaffold = (
            "from __future__ import annotations\n\n"
            "def parse_enabled(value: object) -> bool:\n"
            "    raise NotImplementedError\n"
        )
        behavior = (
            f"Implement parse_enabled(value). Convert to string, trim, lowercase, "
            f"check against {list(tokens)!r}."
        )
    else:  # filename_policy
        separator = rng.choice(["-", "_", "."])
        lowercase = rng.choice([True, False])
        expected = {"separator": separator, "lowercase": lowercase}
        decision = f"Filenames use separator {separator!r}, lowercase={lowercase}."
        scaffold = (
            "from __future__ import annotations\n\n"
            "def artifact_filename(name: str, extension: str) -> str:\n"
            "    raise NotImplementedError\n"
        )
        case_rule = "lowercase the stem" if lowercase else "preserve case"
        behavior = (
            f"Implement artifact_filename(name, extension). Trim, replace whitespace "
            f"with {separator!r}, collapse repeats, {case_rule}, normalize extension "
            "to lowercase without dot."
        )
    
    # Build memory context for memorix_core mode
    memory_context = ""
    if mode == "memorix_core":
        memory_context = (
            "\n\n[MEMORY CONTEXT]\n"
            "You have access to validated project decisions from memory.\n"
            f"Decision: {decision}\n"
            "Use this decision when implementing the function.\n"
            "[/MEMORY CONTEXT]\n\n"
        )
    
    prompt = (
        f"Implement the following Python function.\n\n"
        f"{scaffold}\n"
        f"{behavior}\n"
        f"{memory_context}\n"
        "Write ONLY the function implementation. No tests, no comments, no explanation."
    )
    
    return prompt, expected, scaffold


def _evaluate_solution(
    family_id: str,
    seed: int,
    code: str,
    expected: dict[str, Any],
) -> tuple[bool, int, int]:
    """Evaluate generated code against expected output.
    
    Returns (passed, case_count, passed_case_count).
    """
    kind = FAMILY_TO_KIND.get(family_id)
    
    # Create a temporary module
    module_name = f"bench_eval_{family_id}_{seed}"
    module = type("Module", (), {})()
    
    try:
        exec(code, module.__dict__)
    except Exception:
        return False, 0, 0
    
    cases = []
    
    try:
        if kind == "csv_delimiter":
            delimiter = str(expected["delimiter"])
            test_cases = [
                ([["a", "b"], [1, 2]], f"a{delimiter}b\n1{delimiter}2"),
                ([], ""),
                ([["single"]], "single"),
            ]
            for args, exp in test_cases:
                actual = module.serialize_rows(args)
                cases.append(actual == exp)
        
        elif kind == "username_separator":
            sep = str(expected["separator"])
            test_cases = [
                ("  Alice   Smith  ", f"alice{sep}smith"),
                (f"BOB{sep}{sep}Jones", f"bob{sep}jones"),
                ("Single", "single"),
            ]
            for value, exp in test_cases:
                actual = module.normalize_username(value)
                cases.append(actual == exp)
        
        elif kind == "retry_schedule":
            base = float(expected["base"])
            factor = float(expected["factor"])
            for attempts in [0, 1, 4]:
                exp = [round(base * (factor ** i), 3) for i in range(max(0, attempts))]
                actual = module.retry_delays(attempts)
                cases.append(actual == exp)
        
        elif kind == "date_format":
            from datetime import date
            fmt = str(expected["format"])
            for value in [date(2026, 7, 24), date(2030, 1, 5)]:
                exp = value.strftime(fmt)
                actual = module.format_date(value)
                cases.append(actual == exp)
        
        elif kind == "cache_key":
            sep = str(expected["separator"])
            test_cases = [
                ((" Users ", " 42 "), f"users{sep}42"),
                (("API", "ABC-9"), f"api{sep}ABC-9"),
            ]
            for args, exp in test_cases:
                actual = module.build_cache_key(*args)
                cases.append(actual == exp)
        
        elif kind == "page_size":
            default = int(expected["default"])
            maximum = int(expected["maximum"])
            test_cases = [(None, default), (0, 1), (1, 1), (maximum + 50, maximum), (17, 17)]
            for value, exp in test_cases:
                actual = module.normalize_page_size(value)
                cases.append(actual == exp)
        
        elif kind == "boolean_tokens":
            true_tokens = {str(v).lower() for v in expected["true_tokens"]}
            test_values = list(true_tokens) + [" TRUE ", "false", "0", "disabled"]
            for value in test_values:
                exp = str(value).strip().lower() in true_tokens
                actual = module.parse_enabled(value)
                cases.append(actual is exp)
        
        elif kind == "filename_policy":
            import re
            sep = str(expected["separator"])
            lowercase = bool(expected["lowercase"])
            test_cases = [(" My  Report ", ".PDF"), ("Alpha Beta", "TXT")]
            for name, ext in test_cases:
                stem = re.sub(r"\s+", sep, name.strip())
                stem = re.sub(re.escape(sep) + r"+", sep, stem)
                if lowercase:
                    stem = stem.lower()
                exp = f"{stem}.{ext.lstrip('.').lower()}"
                actual = module.artifact_filename(name, ext)
                cases.append(actual == exp)
    
    except Exception:
        return False, 0, 0
    
    if not cases:
        return False, 0, 0
    
    passed_count = sum(1 for c in cases if c)
    return passed_count == len(cases), len(cases), passed_count


def run_direct(request: DirectRunRequest) -> DirectRunResult:
    """Execute a direct LLM benchmark run."""
    prompt, expected, scaffold = _build_prompt(
        request.family_id,
        request.seed,
        request.mode,
        request.distractor_count,
    )
    
    # Call the LLM backend
    started = time.perf_counter()
    try:
        response = request.backend.generate(
            prompt=prompt,
            max_tokens=1024,
            temperature=0.0,
        )
    except Exception as exc:
        latency_ms = (time.perf_counter() - started) * 1000
        return DirectRunResult(
            family_id=request.family_id,
            seed=request.seed,
            mode=request.mode,
            passed=False,
            exit_code=125,
            timed_out=False,
            duration_ms=round(latency_ms, 3),
            case_count=0,
            passed_case_count=0,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            solution_sha256="",
            generated_code_preview="",
            error=f"BackendError: {exc}",
        )
    
    latency_ms = (time.perf_counter() - started) * 1000
    
    if response.error:
        return DirectRunResult(
            family_id=request.family_id,
            seed=request.seed,
            mode=request.mode,
            passed=False,
            exit_code=1,
            timed_out=False,
            duration_ms=round(latency_ms, 3),
            case_count=0,
            passed_case_count=0,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            total_tokens=response.total_tokens,
            solution_sha256="",
            generated_code_preview=response.text[:500],
            error=response.error,
        )
    
    # Extract code from response (strip markdown fences if present)
    code = response.text.strip()
    if code.startswith("```python"):
        code = code[9:]
    elif code.startswith("```"):
        code = code[3:]
    if code.endswith("```"):
        code = code[:-3]
    code = code.strip()
    
    # If no code generated, try to use the scaffold as fallback
    if not code or "NotImplementedError" in code:
        return DirectRunResult(
            family_id=request.family_id,
            seed=request.seed,
            mode=request.mode,
            passed=False,
            exit_code=1,
            timed_out=False,
            duration_ms=round(latency_ms, 3),
            case_count=0,
            passed_case_count=0,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            total_tokens=response.total_tokens,
            solution_sha256="",
            generated_code_preview=code[:500],
            error="NoImplementation: LLM did not generate valid code",
        )
    
    # Evaluate
    passed, case_count, passed_case_count = _evaluate_solution(
        request.family_id,
        request.seed,
        code,
        expected,
    )
    
    solution_sha = hashlib.sha256(code.encode("utf-8")).hexdigest()
    
    return DirectRunResult(
        family_id=request.family_id,
        seed=request.seed,
        mode=request.mode,
        passed=passed,
        exit_code=0 if passed else 1,
        timed_out=False,
        duration_ms=round(latency_ms, 3),
        case_count=case_count,
        passed_case_count=passed_case_count,
        prompt_tokens=response.prompt_tokens,
        completion_tokens=response.completion_tokens,
        total_tokens=response.total_tokens,
        solution_sha256=solution_sha,
        generated_code_preview=code[:500],
    )


def run_direct_pair(
    family_id: str,
    seed: int,
    backend: LLMBackend,
    timeout_seconds: int = 120,
    distractor_count: int = 50,
    top_k: int = 10,
) -> tuple[DirectRunResult, DirectRunResult]:
    """Execute a no_memory + memorix_core pair using direct LLM.
    
    Returns (no_memory_result, memorix_core_result).
    """
    no_memory = run_direct(DirectRunRequest(
        family_id=family_id,
        seed=seed,
        mode="no_memory",
        backend=backend,
        timeout_seconds=timeout_seconds,
        distractor_count=distractor_count,
        top_k=top_k,
    ))
    
    memorix_core = run_direct(DirectRunRequest(
        family_id=family_id,
        seed=seed,
        mode="memorix_core",
        backend=backend,
        timeout_seconds=timeout_seconds,
        distractor_count=distractor_count,
        top_k=top_k,
    ))
    
    return no_memory, memorix_core


def list_available_families() -> list[str]:
    """Return the list of family IDs that can be run."""
    return sorted(FAMILY_TO_KIND.keys())
