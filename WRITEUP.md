# Writeup

## What I chose and why

**Conduit** (the "RealWorld" reference app) split across
`node-express-sequelize-realworld-example-app` (backend) and
`react-redux-realworld-example-app` (frontend) - two genuinely separate
repos with real authorization logic (article ownership, comment ownership,
favoriting) rather than a toy CRUD demo. I specifically picked the
Sequelize/SQLite variant of the backend over the more common Mongo one
because it has no external service dependency beyond a SQL database, which
matters if a tester repo needs to actually boot the app in CI rather than
just talk about testing it.

## The biggest trade-off I made

I built and ran the API-level tests (`tests/api/*`) for real, in the sandbox
I had, against a live instance of the backend. The browser-based E2E test
(`tests/e2e/*`) is written against real, verified UI selectors, but I could
not execute it in that same sandbox - no route to Playwright's browser-binary
CDN. I chose to still write and commit a real E2E test rather than avoid the
"E2E" requirement entirely, and to be explicit in the README about exactly
what ran where, instead of implying I watched it pass when I didn't. The
trade-off: you're trusting CI's word (and my reading of the JSX) for the E2E
test's correctness rather than my own eyes. I think honest-but-unverified
beats dishonest-but-confident here, but it's a real trade-off, not a free
lunch.

## The single biggest threat to this suite's reliability

**Tests that assert on something that isn't actually the feature.** The
easiest way for a suite like this to become useless is death by a thousand
shallow assertions ("status is 200", "response has a body") that pass no
matter what the app does, while the team's trust in "green means safe"
quietly erodes. I tried to design against this in two places: the manual
Task-1 test asserts on specific business rules (favorite count actually
increments/decrements, not just "the endpoint responds"), and the agent has
a mechanical grounding check plus a `test.fixme` escape hatch specifically so
it can't paper over a gap with a plausible-looking-but-fake assertion. The
second-biggest threat, close behind: **flaky tests that get muted instead of
fixed**, which is why the PR template has an explicit checklist item against
adding unexplained sleeps/timeouts, and why CODEOWNERS puts the automation
engineer in the loop on any change to the tests themselves.

## What I'd build next with more time

1. Point the agent at the whole feature surface (articles + profiles + tags,
   not just one route file at a time) and have it propose *which* behaviors
   are worth testing before generating anything - right now I pick the
   focus by hand.
2. Feed it the model files automatically so the `test.fixme` gaps close
   themselves instead of requiring a human to notice and re-run.
3. A flakiness dashboard - even a dumb one that counts retries-until-pass
   per test in CI over time - since "the suite exists" and "the suite is
   trusted" are different things, and the second one is the actual goal.
