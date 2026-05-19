"""
telephone_etl.py  –  AI Echo Chamber: The Telephone Experiment
==============================================================
Demonstrates how AI guidance drifts when a model is repeatedly asked to
"clarify and improve" its own previous output — a pure echo chamber.

Pipeline:
  Round 0: Ask "How do I make s'mores?"
  Round 1+: Feed the previous answer back with the prompt:
             "Here is a recipe I found online. Please rewrite it to make it
              clearer, more accurate, and easier to follow."
  Repeat N_ROUNDS times.

Each round the AI thinks it's improving the recipe. Instead, it compounds
hallucinations — adding invented temperatures, times, equipment, and brand
names — while the actual s'mores simplicity evaporates.

Usage:
  pip install anthropic
  export ANTHROPIC_API_KEY=sk-ant-...
  python telephone_etl.py

Output:
  telephone_results.json  (consumed by templates/telephone.html)
"""

import os
import json
import re
import anthropic

# ── Config ─────────────────────────────────────────────────────────────────

N_ROUNDS = 6
MODEL = "claude-haiku-4-5-20251001"

SEED_QUESTION = "How do I make s'mores?"

ECHO_PROMPT = (
    "Here is a recipe I found online. Please rewrite it to make it clearer, "
    "more accurate, and easier to follow. Do not add unnecessary complexity — "
    "just improve the clarity and accuracy of what is already here."
)

# ── Similarity (word-level Jaccard) ────────────────────────────────────────

def tokenize(text: str) -> set:
    return set(re.findall(r"\b[a-z0-9']+\b", text.lower()))

def jaccard(a: str, b: str) -> float:
    sa, sb = tokenize(a), tokenize(b)
    if not sa and not sb:
        return 1.0
    return round(len(sa & sb) / len(sa | sb), 4)

def count_steps(text: str) -> int:
    return len([ln for ln in text.splitlines() if ln.strip() and ln.strip()[0].isdigit()])

# ── ETL ─────────────────────────────────────────────────────────────────────

def call_claude(client: anthropic.Anthropic, system: str, user: str) -> str:
    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return response.content[0].text.strip()


def run_pipeline() -> dict:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("Set the ANTHROPIC_API_KEY environment variable first.")

    client = anthropic.Anthropic(api_key=api_key)

    print(f"Round 0: asking \"{SEED_QUESTION}\"…")
    r0_text = call_claude(
        client,
        system="You are a helpful cooking assistant. Give clear, practical instructions.",
        user=SEED_QUESTION,
    )
    print(f"  {len(r0_text.split())} words\n")

    rounds = [
        {
            "round": 0,
            "prompt": SEED_QUESTION,
            "text": r0_text,
            "jaccard": 1.0,
            "word_count": len(r0_text.split()),
            "step_count": count_steps(r0_text),
        }
    ]

    current_text = r0_text

    for i in range(1, N_ROUNDS + 1):
        user_msg = f"{ECHO_PROMPT}\n\n---\n{current_text}"
        print(f"Round {i}: feeding output back into model…")
        current_text = call_claude(
            client,
            system="You are a helpful cooking assistant. Rewrite and improve the following recipe.",
            user=user_msg,
        )
        sim = jaccard(r0_text, current_text)
        wc = len(current_text.split())
        sc = count_steps(current_text)
        print(f"  similarity to original: {sim:.1%} | words: {wc} | steps: {sc}\n")

        rounds.append(
            {
                "round": i,
                "prompt": ECHO_PROMPT,
                "text": current_text,
                "jaccard": sim,
                "word_count": wc,
                "step_count": sc,
            }
        )

    result = {
        "question": SEED_QUESTION,
        "echo_prompt": ECHO_PROMPT,
        "model": MODEL,
        "n_rounds": N_ROUNDS,
        "rounds": rounds,
    }

    out_path = os.path.join(os.path.dirname(__file__), "telephone_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"✓  Results saved to {out_path}")
    return result


if __name__ == "__main__":
    run_pipeline()
