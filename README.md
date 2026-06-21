# You Can't `assert` an LLM: How to Actually Test Non-Deterministic AI

> **AI Engineer Roadmap — Project 6.2 ("Teach it back")**
> A plain-language explainer on building evaluation harnesses for LLM systems —
> the single most underrated skill in AI engineering. Runnable example included:
> [`example.py`](example.py).

If you've built anything on top of an LLM, you've felt this: you tweak a prompt,
the demo looks better, you ship it — and three other things quietly break. You
have no idea, because you have no way to *know*. This article is about closing
that gap.

---

## The problem in one line

**Traditional software is tested with `assert output == expected`. LLM output
isn't equal to anything.**

Ask the same model the same question twice and you get two different sentences
that mean the same thing. Ask it after a prompt change and you might get a better
answer, a worse one, or the same quality phrased differently. `==` is useless
here, so most people fall back to the worst possible test: **reading a few
outputs and going "yeah, seems fine."**

That's not a test. It doesn't scale past five examples, it doesn't catch
regressions, and it can't tell you whether the change you just made helped or
hurt. The fix is an **evaluation harness**: a labelled test set, automated
scoring, and a regression gate you can run on every change.

---

## The four pieces

### 1. A labelled test set

A list of cases: an input, optionally a reference answer, and the **criteria** a
good answer must meet. This is the part everyone skips and the part that matters
most — without ground truth there's nothing to measure against.

```python
cases = [
    {"id": "refund", "input": "How do I get a refund?",
     "criteria": "Explains the refund steps and the time window."},
    {"id": "hours", "input": "What time do you close?",
     "reference": "9pm", "criteria": "States the closing time."},
]
```

You don't need thousands. Twenty good cases that cover your real failure modes
beat a giant vague set. Add a new case **every time something breaks in
production** — your test set becomes a memory of every bug you've fixed.

### 2. Scorers — turn an answer into a number

Two families, and you'll use both:

- **Heuristic scorers** for when there's a clear right answer: exact match,
  substring contains, regex, "is it valid JSON?". Cheap, instant, deterministic.
- **LLM-as-judge** for open-ended answers where no single string is correct. You
  ask *another* LLM to rate the output against the case's criteria on a 0–1 scale
  and explain its reasoning.

The judge sounds circular — *using an LLM to grade an LLM?* — but it works,
because **grading is easier than generating.** Deciding "does this answer explain
the refund window?" is a far simpler task than writing the answer, so a model
(even a cheaper one) is reliable at it. Give it a tight rubric and make it return
structured output:

```python
JUDGE_SYSTEM = (
    "Score the output 0.0–1.0 on whether it meets the criteria. "
    'Respond with ONLY {"score": <0..1>, "reasoning": "<one sentence>"}.'
)
```

> **Pitfall:** parse the judge's reply *defensively*. Models wrap JSON in prose,
> add code fences, or ramble. A malformed verdict should score 0 and move on, not
> crash your whole eval run.

### 3. Aggregate — one number per run

Run every case through your system, score each with every scorer, and roll it up:
**pass rate**, **mean score**, and a per-scorer breakdown. One rule pays for
itself: **a case passes only if *every* scorer passes it.** That stops a fluent,
confident, totally-wrong answer from sneaking through just because it happened to
contain the right keyword.

### 4. The regression gate — did this change help or hurt?

This is the payoff. Store the scores from your current system as a **baseline**.
After any change — new prompt, new model, refactored retrieval — run the eval
again and **diff the two runs case by case**:

- which cases got **worse** (regressed)?
- which got **better** (improved)?
- what's the overall delta?

Wire that into CI: if any case regressed, fail the build. Now a prompt change goes
from "I think it's fine" to **"recall dropped on 2 of 20 cases, here they are"** —
in seconds, automatically, before it reaches users.

```
v1: mean_score=1.000
v2: mean_score=0.775   (after a 'harmless' refactor)
REGRESSED: capital_jp 1.00 -> 0.10,  planets 1.00 -> 0.10
```

That output is the entire point. You changed something, and you *immediately know*
exactly what it broke.

---

## Why this is the underrated skill

Everyone obsesses over prompts and models. But the teams that ship reliable LLM
products aren't the ones with the cleverest prompts — they're the ones who can
**change** their prompts without fear, because a harness tells them within minutes
whether they improved things or regressed them. Evaluation is what turns LLM
development from vibes into engineering.

It's also the most honest signal of seniority. Anyone can demo a happy path.
Being able to say *"here is where this system fails, here's the number, and here's
the test that will catch it if it regresses"* is the difference between someone
who builds demos and someone companies pay.

---

## The mental model that makes it click

Think of your LLM system as a function whose output you can't predict, only
*judge*. You can't pin the output, so you pin the **judgement of the output**:

```
deterministic test:   assert f(x) == expected
LLM harness:          assert judge(f(x), criteria) >= threshold,  on a labelled set,
                      and assert no case got worse than last time
```

Same discipline as a normal test suite — labelled inputs, automated checks, a
gate on every change. You've just moved the assertion from the *output* to a
*scored judgement of the output*. Once that clicks, testing LLMs stops feeling
impossible and starts feeling like... testing.

---

## Try it

[`example.py`](example.py) is a ~60-line, dependency-free harness implementing all
four pieces with a stubbed judge, so you can see a regression get caught:

```bash
python example.py
```

A fuller, tested implementation — heuristic scorers, a real LLM-as-judge with
pluggable providers, and a CI-ready regression gate — is in the companion project:
**[ai-roadmap-4.3-eval-harness](https://github.com/smafnan/ai-roadmap-4.3-eval-harness)**.

---

*Found this useful, or spotted something that made it click (or didn't)? That
feedback is the whole goal of a "teach it back" — open an issue.*
