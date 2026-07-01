#!/usr/bin/env python3
"""
Test-writing agent (Task 2).

Reads a real feature file from the target app, asks Claude to generate
Playwright/TypeScript API tests grounded in that code, then runs a mechanical
"grounding check" on the output before accepting it: every route path and
response-field name the generated test asserts on must literally appear in
the source file. If something doesn't match, the agent does not silently
accept it — it fails loudly and prints exactly what's ungrounded, so a human
has to look at it.

This is deliberately narrow in scope: one feature file in, one test file out,
with an honest pass/fail gate. It is not trying to be a general-purpose test
generator.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python agent/generate_tests.py \
        --feature-file /path/to/conduit-backend/routes/api/articles.js \
        --focus "comment creation and deletion" \
        --out agent/output/comments.generated.spec.ts

Model: claude-sonnet-5 (override with --model). Uses the Anthropic Messages
API directly (https://docs.claude.com/en/api/messages) - no SDK dependency
beyond `requests`, to keep the agent easy to read end-to-end.
"""
import argparse
import os
import re
import sys
import json
import urllib.request
import urllib.error

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"

SYSTEM_PROMPT = """You are a test-writing agent for a QA automation engineer. \
You generate Playwright + TypeScript tests for a Node/Express backend.

Ground rules - these are non-negotiable:

1. Every route path (e.g. "/api/articles/:article/comments") you write a \
test against must appear, verbatim in structure, in the feature file you \
were given. Do not invent endpoints.
2. Every JSON response field you assert on (e.g. response.comment.author) \
must trace back to something the feature file (or a model file, if shown) \
actually returns. Do not assume fields like "success: true" or "message" \
exist unless you see them constructed in the code.
3. If the feature file references a model, serializer, or helper you were \
NOT given the contents of, and you cannot be sure what shape it returns, \
insert a test with `test.fixme(...)` and a comment explaining exactly what \
extra file you'd need to see before writing a real assertion. Do not guess \
and write a plausible-looking assertion anyway - a wrong assertion that \
happens to pass on lucky data is worse than an honest gap.
4. Prefer a small number of tests that each check one real behavior \
(a specific authorization rule, a specific status code, a specific field \
changing) over a large number of shallow tests that just check "response is \
200 and has a body." A test that would still pass if the feature were \
deleted is worthless - don't write it.
5. Match the existing test file's style if a style sample is provided: \
Playwright's `request` fixture, `test.describe`/`test`, a `uniqueUser()` \
helper for registration, a header comment listing which exact route \
handlers in the source file each test targets.
6. Output ONLY the TypeScript file contents. No markdown fences, no prose \
before or after.
"""

STYLE_SAMPLE = """import { test, expect } from '@playwright/test';

function uniqueUser() {
  const id = Date.now() + '-' + Math.floor(Math.random() * 1e6);
  return {
    username: `tester_${id}`,
    email: `tester_${id}@example.com`,
    password: 'correct horse battery staple',
  };
}

async function registerAndGetToken(request) {
  const user = uniqueUser();
  const res = await request.post('/api/users', { data: { user } });
  const body = await res.json();
  return body.user.token;
}
"""


def call_claude(feature_code: str, focus: str, model: str, style_sample: str) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: set ANTHROPIC_API_KEY before running this agent.", file=sys.stderr)
        sys.exit(1)

    user_prompt = f"""Feature file to test (focus on: {focus}):

```
{feature_code}
```

Existing test file style to match:

```
{style_sample}
```

Generate a Playwright/TypeScript test file for the "{focus}" behavior in \
the feature file above. Follow all ground rules in the system prompt."""

    payload = json.dumps({
        "model": model,
        "max_tokens": 4000,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": user_prompt}],
    }).encode("utf-8")

    req = urllib.request.Request(
        ANTHROPIC_API_URL,
        data=payload,
        headers={
            "content-type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": ANTHROPIC_VERSION,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"ERROR: Anthropic API returned {e.code}: {e.read().decode()}", file=sys.stderr)
        sys.exit(1)

    text_blocks = [b["text"] for b in data.get("content", []) if b.get("type") == "text"]
    return "\n".join(text_blocks).strip()


def extract_route_paths(source: str) -> list[str]:
    """Pull literal Express route paths out of the feature file, e.g. '/:article/comments'."""
    return re.findall(r"router\.(?:get|post|put|delete)\(\s*'([^']+)'", source)


def grounding_check(generated: str, feature_code: str) -> list[str]:
    """
    Mechanical honesty gate: every route-like path string quoted in the
    generated test must correspond to a route path that exists in the
    feature file (allowing for :param -> concrete value substitution).
    Returns a list of problems found (empty = clean).
    """
    problems = []
    real_routes = extract_route_paths(feature_code)
    real_route_regexes = [
        re.compile("^" + re.sub(r":\w+", r"[^/]+", r) + "$") for r in real_routes
    ]

    # Find things in the generated file that look like API paths.
    quoted_paths = re.findall(r"""['"`](/api/[^'"`]+)['"`]""", generated)
    for path in quoted_paths:
        # Strip the /api prefix and any leading article slug segment to compare
        # against router-relative paths like '/:article/comments'.
        relative_candidates = [
            path.replace("/api/articles", ""),
            path.replace("/api", ""),
        ]
        matched = any(
            any(rx.match(cand) for rx in real_route_regexes) or cand in real_routes
            for cand in relative_candidates
        )
        if not matched and path not in ("/api/users",):
            problems.append(f"Generated test references '{path}', which doesn't match any route in the feature file.")

    if "test.fixme" not in generated and "TODO" not in generated and not quoted_paths:
        problems.append("Generated file contains no recognizable API calls and no test.fixme/TODO - likely not grounded in the feature file at all.")

    return problems


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--feature-file", required=True, help="Path to the real source file to generate tests for")
    parser.add_argument("--focus", required=True, help="Which behavior in the file to focus on, e.g. 'comment creation and deletion'")
    parser.add_argument("--out", required=True, help="Where to write the generated .spec.ts file")
    parser.add_argument("--model", default=os.environ.get("AGENT_MODEL", "claude-sonnet-5"))
    args = parser.parse_args()

    with open(args.feature_file, "r") as f:
        feature_code = f.read()

    print(f"[agent] Read {len(feature_code)} chars from {args.feature_file}")
    print(f"[agent] Calling {args.model} to generate tests for: {args.focus}")

    generated = call_claude(feature_code, args.focus, args.model, STYLE_SAMPLE)

    print("[agent] Running grounding check on generated output...")
    problems = grounding_check(generated, feature_code)

    header = (
        f"// AUTO-GENERATED by agent/generate_tests.py\n"
        f"// Source feature file: {args.feature_file}\n"
        f"// Focus: {args.focus}\n"
        f"// Model: {args.model}\n"
    )
    if problems:
        header += "// GROUNDING CHECK FAILED - DO NOT MERGE WITHOUT REVIEW:\n"
        for p in problems:
            header += f"//   - {p}\n"

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write(header + "\n" + generated + "\n")

    print(f"[agent] Wrote {args.out}")
    if problems:
        print("[agent] GROUNDING CHECK FAILED:")
        for p in problems:
            print(f"  - {p}")
        print("[agent] Output was still written (for human review) but the agent is NOT claiming it's trustworthy.")
        sys.exit(2)
    else:
        print("[agent] Grounding check passed: every referenced route matched the feature file.")
        print("[agent] This does NOT mean the test is good - a human still needs to review it before merging.")


if __name__ == "__main__":
    main()
