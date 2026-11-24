import { chromium } from '../../frontend/node_modules/@playwright/test/index.mjs';
import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';
import assert from 'node:assert/strict';

console.log('Launching browser');
const browser = await chromium.launch({ headless: true, channel: 'chrome', timeout: 15000 });
console.log('Browser ready');
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(pathToFileURL(resolve('docs/diagrams/database-walkthrough.html')).href, { timeout: 15000 });
  console.log('HTML loaded');
  await page.waitForFunction(() => !!window.gsap);
  assert.equal(await page.locator('#steps button').count(), 11);
  assert.match(await page.locator('#db-status').textContent(), /Reading/);
  await page.getByRole('button', { name: '3. Store copies', exact: true }).click();
  assert.match(await page.locator('#files-state').textContent(), /4 private/);
  assert.match(await page.locator('#session-state').textContent(), /1 active/);
  assert.match(await page.locator('#db-status').textContent(), /Idle/);
  await page.getByRole('button', { name: 'Play walkthrough', exact: true }).click();
  const start = await page.locator('#scrub').inputValue();
  await page.waitForTimeout(900);
  assert(Number(await page.locator('#scrub').inputValue()) > Number(start));
  assert.equal(await page.locator('#packet').getAttribute('opacity'), '1');
  await page.getByRole('button', { name: 'Pause', exact: true }).click();
  const paused = await page.locator('#scrub').inputValue();
  await page.waitForTimeout(150);
  assert.equal(await page.locator('#scrub').inputValue(), paused);
  await page.getByRole('button', { name: '5. Apply preset', exact: true }).click();
  assert.match(await page.locator('#sql').textContent(), /No SQL/);
  assert.equal(await page.locator('#reads').textContent(), '1');
  await page.getByRole('button', { name: '11. Finished', exact: true }).click();
  assert.match(await page.locator('#files-state').textContent(), /0 files/);
  assert.match(await page.locator('#session-state').textContent(), /0 sessions/);
  assert.match(await page.locator('#download-state').textContent(), /saved/);
  await page.locator('#scrub').evaluate(e => { e.value = '90'; e.dispatchEvent(new Event('input', { bubbles: true })); });
  assert.match(await page.locator('#step-title').textContent(), /Open the studio/);
  assert.match(await page.locator('#db-status').textContent(), /Reading/);
  await page.getByRole('button', { name: 'Why is schema_migrations here?', exact: true }).click();
  assert.equal(await page.locator('dialog').evaluate(e => e.open), true);
  await page.getByRole('button', { name: 'Back to the journey', exact: true }).click();
  await page.getByRole('button', { name: '6. Manual edit', exact: true }).click();
  await page.screenshot({ path: 'docs/diagrams/database-walkthrough-preview.png', fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth));
  await page.getByRole('button', { name: 'Next', exact: true }).click();
  assert.match(await page.locator('#step-title').textContent(), /Analyze/);
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.getByRole('button', { name: 'Play walkthrough', exact: true }).click();
  await page.waitForTimeout(700);
  assert.equal(await page.locator('#packet').getAttribute('opacity'), '0');
  assert.deepEqual(errors, []);
  console.log('Passed: offline GSAP loading, 11 scenes, play/pause, packet motion, preset SQL state, cleanup, backward scrub, dialog, mobile layout and reduced motion.');
} finally {
  await browser.close();
}

