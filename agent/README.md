# The test-writing agent

`generate_tests.py` reads one real feature file from the app, asks Claude to
generate Playwright/TypeScript tests grounded in it, then runs a mechanical
**grounding check** before it lets you trust the output.

## Run it

```bash
export ANTHROPIC_API_KEY=sk-ant-...
cd agent
python generate_tests.py \
  --feature-file ../backend-app/routes/api/articles.js \
  --focus "comment creation and deletion" \
  --out output/comments.generated.spec.ts
```

Output:
```
[agent] Read 8214 chars from ../backend-app/routes/api/articles.js
[agent] Calling claude-sonnet-5 to generate tests for: comment creation and deletion
[agent] Running grounding check on generated output...
[agent] Wrote output/comments.generated.spec.ts
[agent] Grounding check passed: every referenced route matched the feature file.
[agent] This does NOT mean the test is good - a human still needs to review it before merging.
```

## How it keeps output honest

Three separate mechanisms, layered, because any one of them alone is easy to
fool:

1. **The system prompt itself** (see `generate_tests.py`) tells the model to
   trace every route path and every asserted response field back to code it
   was actually shown, and to use `test.fixme(...)` with an explanation
   instead of guessing when a field's shape depends on a file it wasn't
   given. This is the cheapest lever and the least reliable one on its own -
   a model can still hallucinate under a prompt that tells it not to.

2. **A mechanical grounding check runs after generation, in Python, not in
   the model.** It regexes every route path the *model* wrote (things like
   `'/api/articles/${article.slug}/comments'`) and every route path
   *actually declared* in the feature file (`router.post('/:article/comments', ...)`),
   and fails loudly if the generated test references a path that doesn't
   exist in the source. This catches the specific, common failure mode of an
   agent inventing a plausible-sounding endpoint. It's intentionally narrow -
   it checks paths, not full response-shape correctness - because a check
   that tries to verify everything ends up being as unreliable as what it's
   checking.

3. **A human still has to review it.** The agent's exit code is non-zero and
   its own log output says so explicitly when the grounding check fails, and
   even on success it prints "this does NOT mean the test is good." The
   `pull_request_template.md` in the repo root has a checklist item for
   exactly this. An agent that reports 100% confidence is the failure mode
   this whole exercise is asking you to design against - so it never does.

## What I'd add with more time

- Feed the agent the referenced model files automatically (follow
  `require('./models')` / `require('../models/comment')` imports) instead of
  requiring a human to notice the gap and re-run with more context - right
  now that's exactly what produces the `test.fixme` in the sample output.
- Turn the grounding check into a real static-analysis pass (parse the JS
  with an actual parser instead of regexing route strings) so it also
  catches things like "asserts a field that's never assigned anywhere in the
  models it *was* shown."
- Have the agent run the test it just generated (against a throwaway DB) as
  part of the same invocation, and report pass/fail/error inline, instead of
  that being a separate manual step.

## Closing the loop (real transcript from this build)

The API test suite (`tests/api/articles-favorite.spec.ts`, written by hand
for Task 1) and the agent's sample output
(`output/comments.generated.spec.ts`) were both run against a live instance
of the backend (Postgres + `node app.js`, booted in the same sandbox this
was built in):

```
Running 2 tests using 1 worker
  ✓  favoriting and unfavoriting an article updates favorited + favoritesCount (313ms)
  ✓  favoriting an existing article without auth is rejected (documents a real defect) (139ms)
  2 passed (1.2s)

Running 4 tests using 1 worker
  ✓  an authenticated user can post a comment, and the response echoes the submitted body (347ms)
  -  comment.author reflects the commenting user's profile fields (username/bio/image/following)  [fixme, skipped]
  ✓  deleting a comment as someone other than its author is rejected with 403 (263ms)
  ✓  deleting your own comment succeeds and removes it (177ms)
  1 skipped
  3 passed (1.7s)
```

Note the "defect" test above isn't a false negative - it's `tests/api`
documenting real behavior it found in the app (see the comment in that file):
`auth.required` throws on a missing token, and the app's production error
handler doesn't special-case that error, so it returns 500 instead of 401.
That's a genuine finding from grounding a test in what the code actually
does instead of what you'd assume it does.
