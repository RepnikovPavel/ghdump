# Architecture notes

ghdump is a single stdlib-only Python 3 script
(`dont_read_me_src/ghdump.py`). There is no build step and no package
layout on purpose — install is a file copy.

## Data flow

1. `GET /repos/{owner}/{repo}/issues?state=...` (paginated, 100/page).
   The issues endpoint also returns PRs; items with a `pull_request`
   key are split out, the rest are issues.
2. `GET /repos/{owner}/{repo}/pulls?state=...` (paginated) — the PRs.
3. Per item: `GET {comments_url}` when `comments > 0`; per PR also
   `GET {review_comments_url}` when `review_comments > 0`.
4. Each item is written twice: raw JSON (API object plus `_comments`
   and, for PRs, `_review_comments`) and a rendered `.md`.
5. `index.json` aggregates per-item summaries and counts.

## Failure handling

- 403/429 with exhausted rate limit: sleep until `X-RateLimit-Reset`
  and retry.
- 5xx and network errors: exponential backoff, up to 6 attempts.
- Anything else: message on stderr, non-zero exit. Partial output
  stays on disk; rerunning overwrites cleanly.

## Auth

Token is read from `$GITHUB_TOKEN` or `$GH_TOKEN`. It is never written
to any output file. Without a token the tool still works, subject to
GitHub's 60 req/h unauthenticated limit.

## Why not GraphQL / gh CLI?

GraphQL needs a token by definition and pagination-by-cursor machinery;
the `gh` CLI is not guaranteed to exist on minimal systems. Plain REST
with urllib keeps the tool a zero-dependency single file.
