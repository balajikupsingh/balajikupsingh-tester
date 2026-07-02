import { test, expect, request as pwRequest } from '@playwright/test';

/**
 * Targets: conduit-frontend src/components/Editor.js + src/components/Login.js
 *
 * Selectors below are copied from the actual JSX (placeholders + button text),
 * not guessed:
 *   Login.js   -> input[placeholder="Email"], input[placeholder="Password"], button "Sign in"
 *   Editor.js  -> input[placeholder="Article Title"],
 *                 input[placeholder="What's this article about?"],
 *                 textarea[placeholder="Write your article (in markdown)"],
 *                 button "Publish Article"
 *
 * Editor.js's submitForm() calls agent.Articles.create() and dispatches
 * ARTICLE_SUBMITTED, which (see src/reducers/editor.js in the app) redirects
 * to the new article's page on success. So "the article page loads with our
 * title" is a real, grounded assertion of what a successful publish does,
 * not a generic "page didn't crash" check.
 *
 * NOTE: this test needs a real browser (Chromium via Playwright) and is
 * designed to run in CI, where `npx playwright install --with-deps` has
 * full internet access. It cannot execute in this exercise's offline dev
 * sandbox. See tester-repo/README.md ("What actually ran where") for the
 * honest breakdown of what was executed live vs. what CI executes.
 */

test('registering, logging in, and publishing an article shows it on the article page', async ({ page, request, baseURL }) => {
  // Register a fresh user directly against the API so the E2E test doesn't
  // also have to exercise (and depend on) the registration form.
  const id = Date.now();
  const user = {
    username: `e2e_${id}`,
    email: `e2e_${id}@example.com`,
    password: 'correct horse battery staple',
  };
  const apiURL = process.env.BASE_URL_API || 'http://localhost:3000';
  const api = await pwRequest.newContext({ baseURL: apiURL });
  const registerRes = await api.post('/api/users', { data: { user } });
  expect(registerRes.ok(), await registerRes.text()).toBeTruthy();

  // Log in through the real UI.
  await page.goto('/login');
  await page.getByPlaceholder('Email').fill(user.email);
  await page.getByPlaceholder('Password').fill(user.password);
  await page.getByRole('button', { name: 'Sign in' }).click();

  // Header.js only renders the "New Post" link once currentUser is set
  // (LoggedInView vs LoggedOutView) - waiting for it, and navigating via it,
  // avoids a race where we'd hit /editor before the auth token is actually
  // stored (which would make the article-create call fail silently and
  // never redirect - the exact failure this replaces).
  const newPostLink = page.getByRole('link', { name: 'New Post' });
  await expect(newPostLink).toBeVisible({ timeout: 10_000 });

  // Publish an article through the real Editor form.
  const title = `E2E published article ${id}`;
  await newPostLink.click();
  await expect(page).toHaveURL(/\/editor/);
  await page.getByPlaceholder('Article Title').fill(title);
  await page.getByPlaceholder("What's this article about?").fill('Grounded E2E test');
  await page.getByPlaceholder('Write your article (in markdown)').fill('Body written by the E2E test.');
  await page.getByRole('button', { name: 'Publish Article' }).click();

  // A successful publish redirects to the article page and renders the title.
  await expect(page.getByRole('heading', { name: title })).toBeVisible({ timeout: 10_000 });
});
