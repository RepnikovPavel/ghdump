#!/usr/bin/env python3
"""ghdump — dump GitHub issues & pull requests of a repository to disk.

Stdlib only. Reads the API token from $GITHUB_TOKEN or $GH_TOKEN (optional,
but recommended: unauthenticated rate limit is 60 req/h).

Output layout:
  <outdir>/
    index.json                 machine-readable summary of everything dumped
    issues/000001.json         raw API item + "_comments"
    issues/000001.md           human-readable rendering
    pull_requests/000042.json  raw API item + "_comments" + "_review_comments"
    pull_requests/000042.md
"""

import argparse
import concurrent.futures
import json
import os
import sys
import time
import urllib.error
import urllib.request

API = "https://api.github.com"
VERSION = "1.1.0"


def make_request(url, token):
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ghdump/" + VERSION,
    }
    if token:
        headers["Authorization"] = "Bearer " + token
    return urllib.request.Request(url, headers=headers)


def get_json(url, token):
    """GET JSON with retry on rate limit / transient server errors.

    Returns (data, headers)."""
    for attempt in range(6):
        try:
            with urllib.request.urlopen(make_request(url, token)) as resp:
                return json.load(resp), resp.headers
        except urllib.error.HTTPError as e:
            remaining = e.headers.get("X-RateLimit-Remaining")
            reset = e.headers.get("X-RateLimit-Reset")
            if e.code in (403, 429) and (remaining == "0" or e.code == 429):
                wait = 60
                if reset and reset.isdigit():
                    wait = max(1, int(reset) - int(time.time()) + 2)
                print("rate limited; sleeping %ds" % wait, file=sys.stderr)
                time.sleep(wait)
                continue
            if e.code >= 500 and attempt < 5:
                time.sleep(2 ** attempt)
                continue
            body = e.read().decode("utf-8", "replace")[:500]
            raise SystemExit("HTTP %s for %s\n%s" % (e.code, url, body))
        except urllib.error.URLError as e:
            if attempt < 5:
                time.sleep(2 ** attempt)
                continue
            raise SystemExit("network error for %s: %s" % (url, e))
    raise SystemExit("gave up on %s" % url)


def get_paginated(url, token):
    """Yield items from a paginated list endpoint by following Link: rel=next
    (works for both page-based and cursor-based pagination)."""
    sep = "&" if "?" in url else "?"
    next_url = url + sep + "per_page=100"
    while next_url:
        items, headers = get_json(next_url, token)
        for it in items:
            yield it
        next_url = None
        link = headers.get("Link", "")
        for part in link.split(","):
            if 'rel="next"' in part:
                next_url = part.split(";")[0].strip().strip("<>")


def user_login(obj):
    u = obj.get("user")
    return u.get("login", "?") if u else "?"


def fmt_comment(c):
    return (
        "### Comment by @%s at %s\n\n%s\n"
        % (user_login(c), c.get("created_at", "?"), c.get("body") or "")
    )


def render_markdown(item, kind, comments, review_comments=None):
    lines = []
    lines.append("# %s #%d: %s" % (kind, item["number"], item.get("title", "")))
    lines.append("")
    lines.append("- state: %s" % item.get("state"))
    if kind == "PR" and item.get("merged_at"):
        lines.append("- merged_at: %s" % item["merged_at"])
    lines.append("- author: @%s" % user_login(item))
    lines.append("- created_at: %s" % item.get("created_at"))
    lines.append("- updated_at: %s" % item.get("updated_at"))
    if item.get("closed_at"):
        lines.append("- closed_at: %s" % item["closed_at"])
    labels = [l["name"] for l in item.get("labels", [])]
    if labels:
        lines.append("- labels: %s" % ", ".join(labels))
    if item.get("assignees"):
        lines.append(
            "- assignees: %s" % ", ".join("@" + a["login"] for a in item["assignees"])
        )
    lines.append("- url: %s" % item.get("html_url"))
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(item.get("body") or "*(no description)*")
    lines.append("")
    if comments:
        lines.append("")
        lines.append("## Comments (%d)" % len(comments))
        lines.append("")
        for c in comments:
            lines.append(fmt_comment(c))
    if review_comments:
        lines.append("")
        lines.append("## Review comments (%d)" % len(review_comments))
        lines.append("")
        for c in review_comments:
            path = c.get("path", "?")
            lines.append("### Review by @%s at %s on `%s`" % (user_login(c), c.get("created_at", "?"), path))
            lines.append("")
            lines.append(c.get("body") or "")
            lines.append("")
    return "\n".join(lines)


def dump_one(item, kind, d, token, no_comments, no_review_comments):
    """Fetch comments for one item and write its .json/.md. Returns index entry."""
    n = item["number"]
    comments = []
    review_comments = []
    if not no_comments and item.get("comments"):
        comments = list(get_paginated(item["comments_url"], token))
    if kind == "PR" and not no_review_comments and item.get("review_comments"):
        review_comments = list(get_paginated(item["review_comments_url"], token))
    raw = dict(item)
    raw["_comments"] = comments
    if kind == "PR":
        raw["_review_comments"] = review_comments
    stem = os.path.join(d, "%06d" % n)
    with open(stem + ".json", "w", encoding="utf-8") as f:
        json.dump(raw, f, ensure_ascii=False, indent=2, sort_keys=True)
    with open(stem + ".md", "w", encoding="utf-8") as f:
        f.write(render_markdown(item, kind, comments, review_comments))
    return {
        "number": n,
        "title": item.get("title", ""),
        "state": item.get("state"),
        "merged_at": item.get("merged_at") if kind == "PR" else None,
        "author": user_login(item),
        "created_at": item.get("created_at"),
        "closed_at": item.get("closed_at"),
        "comments": len(comments),
        "labels": [l["name"] for l in item.get("labels", [])],
        "html_url": item.get("html_url"),
    }


def dump_items(items, kind, subdir, outdir, token, no_comments, no_review_comments,
               jobs):
    d = os.path.join(outdir, subdir)
    os.makedirs(d, exist_ok=True)
    index = []
    total = len(items)
    done = [0]

    def work(item):
        entry = dump_one(item, kind, d, token, no_comments, no_review_comments)
        done[0] += 1
        if done[0] % 25 == 0 or done[0] == total:
            print("  %s: %d/%d" % (subdir, done[0], total), file=sys.stderr)
        return entry

    if jobs <= 1:
        for item in items:
            index.append(work(item))
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as ex:
            index = list(ex.map(work, items))
    index.sort(key=lambda x: x["number"])
    return index


def main():
    p = argparse.ArgumentParser(
        prog="ghdump",
        description="Dump GitHub issues & pull requests of a repo to disk (JSON + Markdown).",
    )
    p.add_argument("repo", help="owner/name, e.g. microsoft/BitNet")
    p.add_argument("outdir", help="output directory")
    p.add_argument(
        "--state",
        choices=["all", "open", "closed"],
        default="all",
        help="which items to dump (default: all)",
    )
    p.add_argument("--no-comments", action="store_true", help="skip comments (fast)")
    p.add_argument(
        "--no-review-comments",
        action="store_true",
        help="skip PR review (inline) comments",
    )
    p.add_argument(
        "-j",
        "--jobs",
        type=int,
        default=8,
        help="parallel workers for per-item fetches (default: 8)",
    )
    p.add_argument("--version", action="version", version="ghdump " + VERSION)
    args = p.parse_args()

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        print(
            "warning: no GITHUB_TOKEN/GH_TOKEN set; unauthenticated limit is 60 req/h",
            file=sys.stderr,
        )

    owner_repo = args.repo.strip("/")
    base = "%s/repos/%s" % (API, owner_repo)
    state = args.state

    # Issues endpoint returns PRs too; split them out.
    print("fetching issue list (state=%s)..." % state, file=sys.stderr)
    issues = []
    for it in get_paginated("%s/issues?state=%s" % (base, state), token):
        if "pull_request" not in it:
            issues.append(it)

    print("fetching pull request list (state=%s)..." % state, file=sys.stderr)
    pulls = list(get_paginated("%s/pulls?state=%s" % (base, state), token))

    print(
        "found %d issues, %d pull requests" % (len(issues), len(pulls)),
        file=sys.stderr,
    )

    os.makedirs(args.outdir, exist_ok=True)
    idx_issues = dump_items(
        issues, "issue", "issues", args.outdir, token, args.no_comments, True,
        args.jobs,
    )
    idx_pulls = dump_items(
        pulls,
        "PR",
        "pull_requests",
        args.outdir,
        token,
        args.no_comments,
        args.no_review_comments,
        args.jobs,
    )

    index = {
        "repo": owner_repo,
        "state": state,
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "tool": "ghdump " + VERSION,
        "counts": {"issues": len(idx_issues), "pull_requests": len(idx_pulls)},
        "issues": idx_issues,
        "pull_requests": idx_pulls,
    }
    with open(os.path.join(args.outdir, "index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    print(
        "done: %d issues, %d pull requests -> %s"
        % (len(idx_issues), len(idx_pulls), args.outdir),
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
