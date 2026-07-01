## What changed and why

## Which app repo / feature does this test?
<!-- link the FE or BE PR this test suite change is meant to cover, if any -->

## Checklist
- [ ] New/changed tests assert on something a real bug would break (not just "status 200")
- [ ] If this test was agent-generated, the grounding check passed - or if it
      didn't, I reviewed the flagged lines and either fixed them or left a
      `test.fixme` with a clear reason
- [ ] `npm run test:api` passes locally
- [ ] `npm run test:e2e` passes locally (or I've noted why it can't run locally, e.g. no browser deps installed)
- [ ] I did not increase flakiness (no new arbitrary `sleep`/timeouts without a comment explaining why)
