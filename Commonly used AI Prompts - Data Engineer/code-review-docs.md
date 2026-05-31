# Code Review & Documentation Prompts

## Explain code
```
Explain this code in plain English: what it does, how it flows, and any non-obvious parts.
Then note bugs, edge cases, or risks.
[paste code]
```

## Review code
```
Review this [language] code for correctness, readability, performance, and security. List
findings by severity (blocker / major / minor) with a suggested fix for each. Be concrete.
[paste code or diff]
```

## Write a PR description
```
Write a clear pull request description for this change. Include: what changed and why,
approach, testing done, and any risks/rollback. Keep it concise.
Diff/summary: [paste]
```

## Write a tech spec / design doc
```
Help me write a design doc for [feature/system]. Sections: problem, goals/non-goals,
proposed approach, alternatives considered, data model, risks, rollout plan. Ask me for
anything missing, then draft it.
```

## README / runbook
```
Write a [README / runbook] for [project/pipeline]. Cover: what it does, setup, how to run,
config, common failures + fixes, and who owns it. Audience: [new team member / on-call].
Details: [paste]
```

## Inline comments / docstrings
```
Add clear comments and docstrings to this code. Explain *why*, not just *what*. Don't change
behavior. Follow [language] conventions.
[paste code]
```

## Architecture explainer
```
Explain the architecture of this system to a [new engineer / manager]: components, data flow,
and key decisions. Use a simple text diagram. Source: [paste code/config/description].
```

## Compare approaches
```
I'm choosing between [approach A] and [approach B] for [problem]. Compare them on
[performance, cost, complexity, maintainability], give a recommendation for my context
[describe], and note when the other choice would win.
```
