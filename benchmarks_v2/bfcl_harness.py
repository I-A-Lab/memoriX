"""BFCL-derived benchmark harness for the memoriX retrieval pipeline.

Self-contained module (standard library only, no imports from
run_memory_benchmark). It generates a deterministic question dataset, builds
memory-augmented prompts, queries a local Ollama model over HTTP, and runs
three benchmark campaigns:

- oracle_pilot: compares the model with and without memory context.
- blind_curation: evaluates corpus retrieval, retrieved value presence, and
  final answer correctness on the memory-augmented prompt.
- robustness: re-runs the memory prompt across several seeds with shuffled
  and extended distractor sets.
"""

from __future__ import annotations

import json
import random
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path

DOMAINS = ("customer", "finance", "healthcare", "notetaker", "student")

_DOMAIN_WEIGHTS = {
    "customer": 30,
    "finance": 25,
    "healthcare": 25,
    "notetaker": 25,
    "student": 50,
}
_WEIGHT_TOTAL = sum(_DOMAIN_WEIGHTS.values())

# (fact prefix, candidate values). A reference fact is "<prefix> <value>",
# so the answerable value always sits at the end of the fact.
_DOMAIN_FACTS = {
    "customer": [
        ("the account PIN format is", ["1234", "5678", "2468", "1357"]),
        ("the preferred contact method is", ["email", "phone", "chat", "mail"]),
        ("the password reset period is", ["90 days", "180 days", "30 days", "60 days"]),
        ("the default account language is", ["English", "Spanish", "French", "German"]),
        ("the support ticket priority is", ["high", "medium", "low", "urgent"]),
    ],
    "finance": [
        ("the savings interest rate is", ["4.5%", "3.25%", "5.0%", "2.75%"]),
        ("the account number is", ["123456", "789012", "456789", "321654"]),
        ("the monthly account fee is", ["9.99", "19.99", "4.99", "14.99"]),
        ("the daily transaction limit is", ["5000", "10000", "2500", "7500"]),
        ("the credit approval score is", ["700", "650", "720", "680"]),
    ],
    "healthcare": [
        ("the patient allergy is", ["penicillin", "aspirin", "sulfa", "latex"]),
        ("the patient blood type is", ["O+", "A-", "B+", "AB-"]),
        ("the prescribed dosage is", ["500 mg", "250 mg", "750 mg", "1000 mg"]),
        ("the medication frequency is", ["twice daily", "once daily", "three times daily", "every other day"]),
        ("the last vaccination date is", ["2024-11-15", "2023-06-01", "2025-01-20", "2022-09-10"]),
    ],
    "notetaker": [
        ("the meeting time is", ["3:00 PM", "10:00 AM", "1:30 PM", "9:00 AM"]),
        ("the action item owner is", ["Alice", "Bob", "Carol", "Dave"]),
        ("the project deadline is", ["Friday", "Monday", "Tuesday", "Thursday"]),
        ("the board decision is", ["approved", "rejected", "deferred", "tabled"]),
        ("the meeting venue is", ["Room 401", "Room 202", "Room 305", "Room 108"]),
    ],
    "student": [
        ("the final exam date is", ["May 15", "June 2", "May 28", "June 10"]),
        ("the assignment weight is", ["20%", "30%", "25%", "15%"]),
        ("the required reading is", ["Chapter 4", "Chapter 7", "Chapter 2", "Chapter 9"]),
        ("the study group time is", ["7:00 PM", "8:00 PM", "6:30 PM", "5:00 PM"]),
        ("the grade cutoff is", ["90", "85", "80", "95"]),
    ],
}

# One 2-3 sentence scenario per fact slot, indexed like _DOMAIN_FACTS.
_DOMAIN_SCENARIOS = {
    "customer": [
        "A customer calls the support line asking about the PIN format used on their stored profile. Based on the account security notes in memory, what is the PIN format?",
        "An account holder wants to know their preferred contact method so the team can send updates. Based on the account preferences in memory, what is the preferred contact method?",
        "A support agent must tell a customer how long their password stays valid before a forced reset. Based on the account security notes in memory, what is the password reset period?",
        "A new agent is preparing an account profile and needs the default language setting. Based on the account profile notes in memory, what is the default account language?",
        "A customer is waiting for help and the team must confirm how urgent their ticket is. Based on the support notes in memory, what is the support ticket priority?",
    ],
    "finance": [
        "A client asks how much their savings account earns each year. Based on the account details in memory, what is the savings interest rate?",
        "A teller needs the client's account number to process a wire transfer. Based on the account details in memory, what is the account number?",
        "A customer asks what they are charged every month for maintaining the account. Based on the account terms in memory, what is the monthly account fee?",
        "A client wants to know how much they can withdraw from an ATM in a single day. Based on the account limits in memory, what is the daily transaction limit?",
        "A loan officer must confirm the minimum score required for credit approval. Based on the lending policy notes in memory, what is the credit approval score?",
    ],
    "healthcare": [
        "A pharmacist checks the patient record before filling a prescription. Based on the patient chart notes in memory, what is the patient allergy?",
        "A lab technician needs the patient's blood type for a transfusion order. Based on the patient chart notes in memory, what is the patient blood type?",
        "A nurse must verify the correct amount of medication to administer. Based on the prescription notes in memory, what is the prescribed dosage?",
        "A caregiver asks how often the medication should be taken during the day. Based on the prescription notes in memory, what is the medication frequency?",
        "A clinic clerk needs the date of the patient's last vaccination for the record. Based on the patient chart notes in memory, what is the last vaccination date?",
    ],
    "notetaker": [
        "After the team meeting, an assistant must confirm the scheduled start time for the follow-up. Based on the meeting notes in memory, what is the meeting time?",
        "A teammate asks who is responsible for the main action item from the last sync. Based on the meeting notes in memory, what is the action item owner?",
        "The project manager asks when the current milestone must be finished. Based on the project notes in memory, what is the project deadline?",
        "A colleague asks whether the board accepted the new proposal. Based on the board notes in memory, what is the board decision?",
        "A participant needs to know where the next session will be held. Based on the meeting notes in memory, what is the meeting venue?",
    ],
    "student": [
        "A student asks when the final exam is scheduled this semester. Based on the course notes in memory, what is the final exam date?",
        "A classmate wants to know how much the term project counts toward the final grade. Based on the syllabus notes in memory, what is the assignment weight?",
        "A student is planning the study schedule and needs to know which part of the textbook to read first. Based on the course notes in memory, what is the required reading?",
        "A group member asks when the weekly study session starts. Based on the study group notes in memory, what is the study group time?",
        "A student wants to know the minimum score needed to receive an A in the course. Based on the grading notes in memory, what is the grade cutoff?",
    ],
}

# Plausible-but-wrong value pool used to synthesize extra distractors during
# the robustness campaign (never collides with dataset values).
_EXTRA_VALUE_POOL = [
    "unknown",
    "not specified",
    "N/A",
    "0000",
    "undefined",
    "blocked",
    "pending",
    "TBD",
]


@dataclass
class BFCLQuestion:
    """A single BFCL-derived retrieval question for the memoriX pipeline."""

    domain: str
    question_id: str
    question_text: str
    reference_fact: str
    distractors: list[str]
    answer_format: str


def _domain_counts(count: int) -> dict[str, int]:
    """Distribute `count` questions across domains proportionally to _DOMAIN_WEIGHTS."""
    count = max(0, count)
    counts = {
        domain: count * weight // _WEIGHT_TOTAL
        for domain, weight in _DOMAIN_WEIGHTS.items()
    }
    remaining = count - sum(counts.values())
    ordered = sorted(
        _DOMAIN_WEIGHTS,
        key=lambda domain: (count * _DOMAIN_WEIGHTS[domain]) % _WEIGHT_TOTAL,
        reverse=True,
    )
    for domain in ordered[:remaining]:
        counts[domain] += 1
    return counts


def _build_distractors(domain: str, chosen_prefix: str, chosen_value: str, rng) -> list[str]:
    """Build 3-5 wrong facts on the same domain for the chosen reference fact."""
    same_subject = []
    other_subject = []
    for prefix, values in _DOMAIN_FACTS[domain]:
        for value in values:
            if prefix == chosen_prefix and value == chosen_value:
                continue
            fact = f"{prefix} {value}"
            if prefix == chosen_prefix:
                same_subject.append(fact)
            else:
                other_subject.append(fact)
    n_distractors = rng.randint(3, 5)
    chosen = list(same_subject)
    remaining_slots = n_distractors - len(chosen)
    if remaining_slots > 0:
        chosen += rng.sample(other_subject, min(remaining_slots, len(other_subject)))
    rng.shuffle(chosen)
    return chosen[:n_distractors]


def generate_bfcl_dataset(count: int = 155, rng=None) -> list[BFCLQuestion]:
    """Generate a deterministic BFCL-derived dataset of `count` questions.

    Domain split: customer 30, finance 25, healthcare 25, notetaker 25,
    student 50 for the default count of 155 (proportional for other counts).
    Uses `rng` when provided, otherwise a random.Random(42) instance.
    """
    if rng is None:
        rng = random.Random(42)
    questions = []
    for domain in DOMAINS:
        n_questions = _domain_counts(count)[domain]
        facts = _DOMAIN_FACTS[domain]
        scenarios = _DOMAIN_SCENARIOS[domain]
        for index in range(1, n_questions + 1):
            fact_index = rng.randrange(len(facts))
            prefix, values = facts[fact_index]
            value = rng.choice(values)
            questions.append(
                BFCLQuestion(
                    domain=domain,
                    question_id=f"bfcl_{domain}_{index:03d}",
                    question_text=scenarios[fact_index],
                    reference_fact=f"{prefix} {value}",
                    distractors=_build_distractors(domain, prefix, value, rng),
                    answer_format="Answer in the exact format: VALUE",
                )
            )
    return questions


def extract_value(reference_fact: str) -> str:
    """Extract the value token after the last "is "/"are " in the fact.

    The value is stripped of trailing punctuation and whitespace.
    """
    idx = -1
    marker_len = 0
    for marker in (" is ", " are "):
        found = reference_fact.rfind(marker)
        if found > idx:
            idx = found
            marker_len = len(marker)
    if idx == -1:
        return reference_fact.strip()
    value = reference_fact[idx + marker_len :].strip()
    return value.rstrip(" \t\n.,!?;:'\"")


def is_answer_correct(response: str, reference_fact: str) -> bool:
    """True when extract_value(reference_fact) appears in the response."""
    return extract_value(reference_fact) in (response or "")


def build_prompt(question: BFCLQuestion, include_memory: bool) -> str:
    """Build the model prompt with or without the memory context block."""
    if include_memory:
        memory_entries = [question.reference_fact, *question.distractors]
        memory_block = "\n".join(f"- {entry}" for entry in memory_entries)
        return (
            f"{question.question_text}\n\n"
            f"[MEMORY CONTEXT]\n{memory_block}\n\n"
            "Use these decisions when answering.\n\n"
            f"{question.answer_format}"
        )
    return f"{question.question_text}\n\n{question.answer_format}"


def call_ollama(model: str, prompt: str, timeout: int = 60) -> str:
    """POST a completion request to the local Ollama server and return the text."""
    payload = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": 512, "temperature": 0.0},
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        "http://localhost:11434/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data.get("response", "")
    except Exception as exc:
        # The harness must survive server outages; an error string never
        # contains the reference value, so correctness checks stay False.
        return f"[ollama_error: {exc}]"


def run_oracle_pilot(questions, model, timeout=60) -> dict:
    """Compare the model with and without memory context per question."""
    results = []
    baseline_correct = 0
    memorix_correct = 0
    for question in questions:
        baseline_response = call_ollama(model, build_prompt(question, False), timeout)
        time.sleep(0.1)
        memorix_response = call_ollama(model, build_prompt(question, True), timeout)
        time.sleep(0.1)
        is_baseline = is_answer_correct(baseline_response, question.reference_fact)
        is_memorix = is_answer_correct(memorix_response, question.reference_fact)
        baseline_correct += int(is_baseline)
        memorix_correct += int(is_memorix)
        results.append(
            {
                "question_id": question.question_id,
                "domain": question.domain,
                "baseline_correct": is_baseline,
                "memorix_correct": is_memorix,
                "baseline_response": baseline_response,
                "memorix_response": memorix_response,
            }
        )
    total_pairs = len(questions)
    return {
        "campaign": "oracle_pilot",
        "results": results,
        "summary": {
            "total_pairs": total_pairs,
            "baseline_correct": baseline_correct,
            "memorix_correct": memorix_correct,
            "rate_memorix": memorix_correct / total_pairs if total_pairs else 0.0,
        },
    }


def run_blind_curation(questions, model, timeout=60) -> dict:
    """Evaluate corpus retrieval, retrieved value presence, and final answer."""
    results = []
    corpus_ok_total = 0
    retrieval_ok_total = 0
    correct_total = 0
    for question in questions:
        response = call_ollama(model, build_prompt(question, True), timeout)
        time.sleep(0.1)
        corpus_ok = True  # simulation: the memory block always contains the fact
        retrieval_ok = extract_value(question.reference_fact) in response
        correct = is_answer_correct(response, question.reference_fact)
        corpus_ok_total += int(corpus_ok)
        retrieval_ok_total += int(retrieval_ok)
        correct_total += int(correct)
        results.append(
            {
                "question_id": question.question_id,
                "domain": question.domain,
                "corpus_contains_reference": corpus_ok,
                "retrieval_contains_reference": retrieval_ok,
                "correct_answer": correct,
                "response": response,
            }
        )
    total = len(questions)
    return {
        "campaign": "blind_curation",
        "results": results,
        "summary": {
            "total_questions": total,
            "corpus_contains_reference": corpus_ok_total,
            "retrieval_contains_reference": retrieval_ok_total,
            "correct_answer": correct_total,
            "rate_corpus_contains_reference": corpus_ok_total / total if total else 0.0,
            "rate_retrieval_contains_reference": retrieval_ok_total / total if total else 0.0,
            "rate_correct_answer": correct_total / total if total else 0.0,
        },
    }


def _extra_distractors(question: BFCLQuestion, rng) -> list[str]:
    """Build 2 new wrong facts for the question, derived from its value prefix."""
    fact = question.reference_fact
    value = extract_value(fact)
    value_index = fact.rfind(value)
    prefix = fact[:value_index].rstrip() if value_index != -1 else fact
    extras = []
    candidates = list(_EXTRA_VALUE_POOL)
    rng.shuffle(candidates)
    for candidate in candidates:
        if candidate == value:
            continue
        extra = f"{prefix} {candidate}"
        if extra != fact and extra not in question.distractors and extra not in extras:
            extras.append(extra)
        if len(extras) == 2:
            break
    for index in range(1, 3):
        if len(extras) >= 2:
            break
        extra = f"{prefix} value_{index}"
        if extra != fact and extra not in question.distractors and extra not in extras:
            extras.append(extra)
    return extras


def run_robustness(questions, model, timeout=60, seeds=(1, 2, 3)) -> dict:
    """Re-run the memory prompt across seeds with shuffled, extended distractors."""
    results = []
    corpus_ok_total = 0
    retrieval_ok_total = 0
    correct_total = 0
    total_runs = 0
    successful_all_seeds = 0
    successful_at_least_2 = 0
    for question in questions:
        per_seed_correct = {}
        for seed in seeds:
            seed_rng = random.Random(seed)
            distractors = list(question.distractors)
            seed_rng.shuffle(distractors)
            distractors += _extra_distractors(question, seed_rng)
            variant = BFCLQuestion(
                domain=question.domain,
                question_id=question.question_id,
                question_text=question.question_text,
                reference_fact=question.reference_fact,
                distractors=distractors,
                answer_format=question.answer_format,
            )
            response = call_ollama(model, build_prompt(variant, True), timeout)
            time.sleep(0.1)
            corpus_ok = True  # simulation: the memory block always contains the fact
            retrieval_ok = extract_value(question.reference_fact) in response
            correct = is_answer_correct(response, question.reference_fact)
            corpus_ok_total += int(corpus_ok)
            retrieval_ok_total += int(retrieval_ok)
            correct_total += int(correct)
            total_runs += 1
            per_seed_correct[seed] = correct
            results.append(
                {
                    "question_id": question.question_id,
                    "domain": question.domain,
                    "seed": seed,
                    "corpus_contains_reference": corpus_ok,
                    "retrieval_contains_reference": retrieval_ok,
                    "correct_answer": correct,
                    "response": response,
                }
            )
        correct_seeds = sum(1 for ok in per_seed_correct.values() if ok)
        if correct_seeds == len(seeds):
            successful_all_seeds += 1
        if correct_seeds >= 2:
            successful_at_least_2 += 1
    return {
        "campaign": "robustness",
        "results": results,
        "summary": {
            "total_cases": len(questions),
            "total_runs": total_runs,
            "corpus_contains_reference": corpus_ok_total,
            "retrieval_contains_reference": retrieval_ok_total,
            "correct_answer": correct_total,
            "cases_successful_3of3": successful_all_seeds,
            "cases_successful_at_least_2of3": successful_at_least_2,
        },
    }


def save_bfcl_results(output_dir, campaign: str, data: dict) -> Path:
    """Persist a campaign report as JSON and return the written path."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    report_path = output_path / f"{campaign}_report.json"
    report_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return report_path


if __name__ == "__main__":
    dataset = generate_bfcl_dataset(10)
    for question in dataset:
        print(
            f"{question.question_id} [{question.domain}] "
            f"value={extract_value(question.reference_fact)!r} "
            f"distractors={len(question.distractors)}"
        )
    print(f"total questions: {len(dataset)}")
