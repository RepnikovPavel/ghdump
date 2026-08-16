# ghdump

Dumps GitHub issues & pull requests of a repository to disk — both
machine-readable JSON and human-readable Markdown, comments included.
Stdlib-only Python 3, no pip packages needed.

Output layout:

```
<outdir>/
  index.json                 summary of everything dumped
  issues/000001.json         raw API item + "_comments"
  issues/000001.md           human-readable rendering
  pull_requests/000042.json  raw API item + "_comments" + "_review_comments"
  pull_requests/000042.md
```

## Install

Requires Python 3.8+.

```sh
git clone https://github.com/RepnikovPavel/ghdump.git
cd ghdump
./install.sh                 # installs to ~/.local/bin/ghdump
# or system-wide:
sudo ./install.sh /usr/local/bin
```

## Usage

```sh
export GITHUB_TOKEN=...      # or GH_TOKEN; optional but recommended
                             # (unauthenticated limit is 60 req/h)
ghdump microsoft/BitNet ./dump        # all issues + all PRs
ghdump microsoft/BitNet ./dump --state open
ghdump microsoft/BitNet ./dump --no-comments   # fast, metadata only
ghdump --help
```

Flags: `--state all|open|closed` · `--no-comments` · `--no-review-comments`.

## For AI agents

Feed agents `prompt.txt` — a minimal, low-token brief of what ghdump
does and how to call it. Project structure is intentionally
self-describing:

- `dont_read_me_src/` — the source code (no need to read it).
- `if_necessary_you_can_read_me/` — architecture notes.
- `read_me_if_it_is_not_installed/` — install guides.

## License

0BSD — do whatever you want. See LICENSE.
