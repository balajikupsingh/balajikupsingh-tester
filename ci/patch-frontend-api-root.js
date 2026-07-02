#!/usr/bin/env node
/**
 * The frontend under test (src/agent.js) hardcodes API_ROOT to the public
 * demo backend (https://conduit.productionready.io/api) instead of reading
 * it from an environment variable. That means every request the UI makes -
 * including login - goes to a totally different server than the one our
 * tests register users against, so login silently fails against a user
 * that server has never heard of.
 *
 * This makes API_ROOT configurable via REACT_APP_API_ROOT (Create React
 * App bakes REACT_APP_* env vars into the build at build/start time), and
 * fails loudly if the expected line isn't found rather than silently
 * doing nothing.
 *
 * Usage: node ci/patch-frontend-api-root.js <path-to-frontend-repo>/src/agent.js
 */
const fs = require('fs');

const target = process.argv[2];
if (!target) {
  console.error('Usage: node patch-frontend-api-root.js <path-to-src/agent.js>');
  process.exit(1);
}

const original = fs.readFileSync(target, 'utf8');

const needle = `const API_ROOT = 'https://conduit.productionready.io/api';`;
const replacement = `const API_ROOT = process.env.REACT_APP_API_ROOT || 'https://conduit.productionready.io/api';`;

if (!original.includes(needle)) {
  console.error(
    `ERROR: ${target} doesn't contain the expected hardcoded API_ROOT line.\n` +
    `The upstream frontend repo may have changed - re-check this patch by hand ` +
    `instead of trusting it blindly.`
  );
  process.exit(1);
}

fs.writeFileSync(target, original.replace(needle, replacement));
console.log(`Patched ${target}: API_ROOT now reads REACT_APP_API_ROOT (CI sets this to the local backend).`);
