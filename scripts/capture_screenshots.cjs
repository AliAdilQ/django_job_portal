/* Optional verification tool: npm install --no-save playwright, then node this file. */
const { chromium } = require('playwright');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

const root = path.resolve(__dirname, '..');
const base = process.env.PORTAL_URL || 'http://127.0.0.1:8000';

async function main() {
  fs.mkdirSync(path.join(root, 'screenshots'), { recursive: true });
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1024 }, deviceScaleFactor: 1 });
  const page = await context.newPage();
  const failures = [];
  page.on('pageerror', error => failures.push(error.message));
  page.on('response', response => {
    if (response.status() >= 400 && response.url().startsWith(base)) failures.push(`${response.status()} ${response.url()}`);
  });
  async function visit(route) {
    const response = await page.goto(base + route, { waitUntil: 'networkidle' });
    assert.equal(response.status(), 200, route);
    await page.evaluate(() => document.fonts.ready);
  }
  async function screenshot(name) {
    await page.screenshot({ path: path.join(root, 'screenshots', name + '.png'), fullPage: true });
    console.log(`Captured ${name}.png`);
  }
  async function login(email, password) {
    await visit('/accounts/login/');
    await page.getByLabel('Email or username').fill(email);
    await page.locator('#id_password').fill(password);
    await Promise.all([page.waitForURL(/dashboard/), page.getByRole('button', { name: 'Log in', exact: true }).click()]);
    await page.waitForLoadState('networkidle');
  }
  async function logout() {
    await Promise.all([page.waitForURL(base + '/'), page.getByRole('button', { name: 'Logout', exact: true }).click()]);
  }
  await visit('/');
  await page.getByRole('heading', { name: /Find your.*dream job/ }).waitFor();
  await screenshot('home');
  await visit('/jobs/');
  await screenshot('jobs');
  const jobURL = await page.locator('.job-card h3 a').first().getAttribute('href');
  await visit(jobURL);
  await screenshot('job-detail');
  await visit('/accounts/login/');
  await screenshot('login');
  await login('jobseeker@example.com', 'JobSeeker123!');
  await visit('/dashboard/seeker/');
  await screenshot('jobseeker-dashboard');
  await visit('/applications/mine/');
  await visit('/jobs/saved/');
  await visit('/accounts/profile/');
  await logout();
  await login('employer@example.com', 'Employer123!');
  await visit('/dashboard/employer/');
  await screenshot('employer-dashboard');
  await visit('/jobs/manage/');
  await visit('/jobs/new/');
  await visit('/accounts/company/');
  await visit('/applications/received/');
  const applicationURL = await page.locator('.portal-table .circle-link').first().getAttribute('href');
  await visit(applicationURL);
  await logout();
  await login('admin', 'Admin12345!');
  await visit('/dashboard/admin/');
  await screenshot('admin-dashboard');
  for (const resource of ['users', 'companies', 'jobs', 'applications', 'categories', 'saved-jobs']) await visit(`/dashboard/admin/${resource}/`);
  await visit('/admin/');
  await visit('/dashboard/admin/');
  await logout();

  // Check narrow-screen layout and the Bootstrap navigation toggle.
  await page.setViewportSize({ width: 390, height: 844 });
  for (const route of ['/', '/jobs/', jobURL, '/accounts/login/', '/accounts/register/', '/companies/', '/categories/']) {
    await visit(route);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1);
    assert.equal(overflow, false, `Horizontal overflow at ${route}`);
  }
  await visit('/');
  await page.getByRole('button', { name: 'Toggle navigation' }).click();
  await page.locator('#mainNav.show').waitFor();
  await page.getByRole('button', { name: 'Toggle navigation' }).click();
  await page.locator('#mainNav.show').waitFor({ state: 'hidden' });
  await screenshot('home-mobile');
  await login('jobseeker@example.com', 'JobSeeker123!');
  await visit('/dashboard/seeker/');
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), false, 'Mobile dashboard overflow');
  await screenshot('jobseeker-dashboard-mobile');
  assert.deepEqual(failures, [], 'Browser errors or failed responses');
  await browser.close();
  console.log('All browser checks passed. 9 real screenshots saved.');
}
main().catch(error => { console.error(error); process.exit(1); });
