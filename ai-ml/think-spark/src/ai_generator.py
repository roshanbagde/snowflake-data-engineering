"""
AI question generation for ThinkSpark.
Builds a structured prompt, calls the LLM, and parses the JSON response.
"""

import json
import re
from typing import Dict, List, Optional

from src.llm_provider import call_llm_text


_SYSTEM = """You are an expert educational psychologist and curriculum designer
specialising in critical thinking, social-emotional learning, and character development for children.
You create thought-provoking questions that have NO single correct answer —
the goal is to make the child THINK, reason, reflect, and articulate their perspective."""

_TYPE_DESCRIPTIONS = {
    "scenario":      "A realistic situation the child must navigate (What would you do if...)",
    "dilemma":       "Two valid options both with real trade-offs — forces weighing competing values",
    "reflection":    "Turns the lens inward — the child reflects on their own behaviour or feelings",
    "debate_starter":"A provocative statement with no clear answer, designed to spark discussion",
    "creative":      "Open-ended imagination prompt — no wrong answer, encourages divergent thinking",
    "what_if":       "Hypothetical world-building — explores consequences and values through imagination",
    "puzzle":        "A lateral-thinking or logic puzzle — one clever answer the child must reason their way to; the journey matters more than the answer",
}


def _build_prompt(
    topic:       str,
    age_group:   str,
    min_age:     int,
    max_age:     int,
    level:       str,
    q_type:      str,
    count:       int,
    language:    str,
    topic_hint:  str,
) -> str:
    type_desc = _TYPE_DESCRIPTIONS.get(q_type, q_type)
    lang_line = f"\nWrite all content in **{language}**." if language != "English" else ""
    hint_line = f"\nAdditional context/theme: {topic_hint.strip()}" if topic_hint.strip() else ""

    if q_type == "puzzle":
        answer_rule = (
            "Puzzles have ONE correct answer — the goal is to make the child REASON their way there. "
            "The hint should guide without giving it away. The sample_answer must include the solution AND a clear explanation of the reasoning."
        )
        level_meaning = (
            "simple: short riddles with a clear logical step; "
            "medium: multi-step lateral thinking with an unexpected twist; "
            "hard: complex logic requiring systematic elimination or creative leaps"
        )
    else:
        answer_rule = "No question should have a single correct answer"
        level_meaning = (
            "straightforward scenarios with clear emotions" if level == "simple"
            else "moderate complexity with some nuance" if level == "medium"
            else "complex scenarios requiring multi-perspective thinking"
        )

    return f"""{_SYSTEM}

Generate exactly {count} questions with the following parameters:
- Topic domain: {topic}
- Age group: {age_group} (ages {min_age}–{max_age})
- Difficulty level: {level}
- Question type: {q_type} — {type_desc}
- Language: {language}{lang_line}{hint_line}

Requirements per question:
1. question_text: The core question (appropriate vocabulary for age {min_age}–{max_age})
2. context: A short scene-setting sentence or two (optional but helpful; empty string if not needed)
3. hint: A nudge to help if the child is stuck — NOT the answer, just a guiding thought
4. sample_answer: A thoughtful example response (for the facilitator's eyes only, not shown to students)
5. discussion_points: Exactly 3 follow-up prompts to deepen the conversation (list of strings)
6. follow_up_questions: Exactly 2 child-level extension questions that build on the answer (list of strings)
7. tags: A comma-separated string of 3–5 relevant keywords

IMPORTANT rules:
- {answer_rule}
- Vocabulary and scenario complexity must match age {min_age}–{max_age}
- Level "{level}" means: {level_meaning}
- Each question must be genuinely different from the others

Respond ONLY with valid JSON in this exact format (no markdown, no explanation):
{{
  "questions": [
    {{
      "question_text": "...",
      "context": "...",
      "hint": "...",
      "sample_answer": "...",
      "discussion_points": ["...", "...", "..."],
      "follow_up_questions": ["...", "..."],
      "tags": "..."
    }}
  ]
}}"""


def _parse_response(raw: str) -> List[Dict]:
    """Extract JSON from LLM response, handling markdown code fences and <think> blocks."""
    # Strip <think>...</think> reasoning blocks (DeepSeek R1, etc.)
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    # Strip markdown code fences
    raw = re.sub(r"```(?:json)?\s*", "", raw).strip()
    raw = raw.rstrip("`").strip()

    # Find the outermost JSON object
    start = raw.find("{")
    end   = raw.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError("No JSON object found in response")

    data = json.loads(raw[start:end])
    questions = data.get("questions", [])
    if not questions:
        raise ValueError("'questions' key missing or empty in response")

    # Normalise fields
    result = []
    for q in questions:
        result.append({
            "question_text":      str(q.get("question_text", "")).strip(),
            "context":            str(q.get("context", "")).strip(),
            "hint":               str(q.get("hint", "")).strip(),
            "sample_answer":      str(q.get("sample_answer", "")).strip(),
            "discussion_points":  [str(p).strip() for p in q.get("discussion_points", [])],
            "follow_up_questions":[str(p).strip() for p in q.get("follow_up_questions", [])],
            "tags":               str(q.get("tags", "")).strip(),
        })
    return result


def generate_questions(
    provider:    str,
    api_key:     str,
    model:       str,
    topic:       str,
    age_group:   str,
    min_age:     int,
    max_age:     int,
    level:       str,
    q_type:      str,
    count:       int       = 5,
    language:    str       = "English",
    topic_hint:  str       = "",
) -> List[Dict]:
    """
    Generate questions via AI. Returns list of question dicts ready for review.
    Raises ValueError on parse failure.
    """
    prompt = _build_prompt(
        topic=topic, age_group=age_group, min_age=min_age, max_age=max_age,
        level=level, q_type=q_type, count=count, language=language,
        topic_hint=topic_hint,
    )
    raw = call_llm_text(
        provider=provider, api_key=api_key, model=model,
        prompt=prompt, max_tokens=8192,
    )
    return _parse_response(raw)
