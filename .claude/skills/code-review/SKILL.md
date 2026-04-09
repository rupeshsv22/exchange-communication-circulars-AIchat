---
name: code-review
description: Use when reviewing code, auditing a PR, or checking for issues. Triggers on review, audit, check, or critique requests.
---

# Code Review Checklist

Prioritize in this order:

1. **Security** — SQL injection, secrets in code, unvalidated input, SSRF, auth bypass, insecure deserialization
2. **Correctness** — race conditions, off-by-one, missing error paths, incorrect async usage
3. **Performance** — N+1 queries, missing indexes, unbounded loops, sync I/O in async, memory leaks
4. **Architecture** — layering violations, tight coupling, circular imports, god objects
5. **Maintainability** — unclear naming, missing types, dead code, duplication, test gaps

## Output format
- Flag severity: 🔴 blocker / 🟡 should-fix / 🟢 nit
- Root cause first, then fix
- Quote the exact line, don't paraphrase
- No praise padding