#!/usr/bin/env node
/**
 * The backend under test (models/index.js) hardcodes `ssl: { require: true }`
 * for its Postgres connection - reasonable for its original target (Heroku
 * Postgres, which requires TLS), but our CI/local Postgres container doesn't
 * support TLS at all, so the connection is rejected outright.
 *
 * This script makes that requirement configurable via PGSSL=false instead of
 * silently patching around it - if the exact block below doesn't match
 * (e.g. the upstream app changed), it fails loudly rather than silently
 * doing nothing, so CI won't pass against code this patch no longer applies to.
 *
 * Usage: node ci/patch-backend-ssl.js <path-to-backend-repo>/models/index.js
 */
const fs = require('fs');

const target = process.argv[2];
if (!target) {
  console.error('Usage: node patch-backend-ssl.js <path-to-models/index.js>');
  process.exit(1);
}

const original = fs.readFileSync(target, 'utf8');

const needle = `    sequelizeParams.dialectOptions = {
      // https://stackoverflow.com/questions/27687546/cant-connect-to-heroku-postgresql-database-from-local-node-app-with-sequelize
      // https://devcenter.heroku.com/articles/heroku-postgresql#connecting-in-node-js
      // https://stackoverflow.com/questions/58965011/sequelizeconnectionerror-self-signed-certificate
      ssl: {
        require: true,
        rejectUnauthorized: false
      }
    };`;

const replacement = `    if (process.env.PGSSL !== 'false') {
      sequelizeParams.dialectOptions = {
        ssl: { require: true, rejectUnauthorized: false }
      };
    }`;

if (!original.includes(needle)) {
  console.error(
    `ERROR: ${target} doesn't match the expected SSL block.\n` +
    `The upstream backend repo may have changed - re-check this patch by hand ` +
    `instead of trusting it blindly.`
  );
  process.exit(1);
}

fs.writeFileSync(target, original.replace(needle, replacement));
console.log(`Patched ${target}: Postgres SSL is now opt-out via PGSSL=false (CI sets this).`);
