# Prompt Engineering Prompts

## The core template (role + context + task + format)
```
You are a [role/expertise].
Context: [background, constraints, audience].
Task: [exactly what you want].
Format: [bullets / table / JSON / word count / tone].
If anything is ambiguous, ask before answering.
```

## Improve my prompt
```
Improve this prompt so the AI gives a better, more reliable answer. Point out what's vague,
add missing context/constraints, and specify the output format. Return the rewritten prompt.
My prompt: "[paste]"
```

## Few-shot pattern
```
Here are examples of the input->output I want:
Input: [ex1 in]  -> Output: [ex1 out]
Input: [ex2 in]  -> Output: [ex2 out]
Now do the same for: [new input]. Match the style and format of the examples exactly.
```

## Make output structured
```
[Your task]. Return ONLY valid JSON matching this schema:
{ "field1": "...", "field2": [...] }
No prose, no markdown fences.
```

## Role-play / persona
```
Act as [persona, e.g. "a skeptical staff engineer reviewing my design"]. Stay in role.
[Task]. Push back where I'm wrong and ask clarifying questions.
```

## Step-by-step reasoning
```
Work through this step by step before giving the final answer. Show your reasoning, then
end with a clear "Answer:" line.
Problem: [paste]
```

## Summarize a long doc
```
Summarize the text below for [audience]. Give: (1) a 2-sentence TL;DR, (2) 5 key points,
(3) any action items. Keep it under [N] words.
[paste text]
```

## Build a reusable template
```
Help me build a reusable prompt template for this recurring task: [describe]. Use
[placeholders] for the parts that change, and explain how to fill each one.
```

## Critique / red-team an answer
```
Critique the answer below: what's wrong, unsupported, or risky? What did it miss? Then give
a corrected version.
[paste answer]
```
