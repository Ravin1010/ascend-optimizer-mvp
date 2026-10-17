import { chromium } from 'playwright';
import fs from 'node:fs/promises';
import path from 'node:path';

const BASE_URL = process.env.DEMO_URL ?? 'http://127.0.0.1:3000';
const OUTPUT_DIR = path.resolve(process.env.DEMO_OUTPUT_DIR ?? 'demo-output');
const OUTPUT_FILE = path.join(OUTPUT_DIR, 'ascend-optimizer-live-demo.webm');

const pause = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function submitAndWait(page, optimize, profileName, modeName) {
  await optimize.click();

  // Wait until the request finishes. The button is disabled and labelled
  // "Assessing…" while the API call is in flight.
  await page.getByRole('button', { name: 'Optimize Decision Sleeve' })
    .waitFor({ state: 'visible', timeout: 60_000 });

  const resultMarker = page.getByText('Policy-Aware Amount Optimizer', { exact: true });
  const errorBox = page.locator('.errorBox');

  const outcome = await Promise.race([
    resultMarker.waitFor({ state: 'visible', timeout: 60_000 }).then(() => 'result'),
    errorBox.waitFor({ state: 'visible', timeout: 60_000 }).then(() => 'error'),
  ]);

  if (outcome === 'error') {
    const message = (await errorBox.innerText()).trim();
    throw new Error(`Dashboard API failed for ${profileName} / ${modeName}: ${message}`);
  }

  // Confirm the rendered result corresponds to the requested profile/mode.
  await page.waitForFunction(
    ({ expectedProfile, expectedMode }) => {
      const text = document.body.innerText;
      const profileReady = text.includes(expectedProfile);
      const modeReady = expectedMode === 'SYNTHETIC_EVALUATION_ONLY'
        ? text.includes('Synthetic Evaluation Only')
        : text.includes('Production Evidence: Unresolved');
      return profileReady && modeReady;
    },
    { expectedProfile: profileName, expectedMode: modeName },
    { timeout: 15_000 },
  );
}

async function scrollTo(page, locator, holdMs = 4500) {
  await locator.scrollIntoViewIfNeeded();
  await page.evaluate(() => window.scrollBy({ top: -90, behavior: 'smooth' }));
  await pause(900);
  await pause(holdMs);
}

await fs.mkdir(OUTPUT_DIR, { recursive: true });

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  viewport: { width: 1440, height: 900 },
  recordVideo: {
    dir: OUTPUT_DIR,
    size: { width: 1440, height: 900 },
  },
});

const page = await context.newPage();
const video = page.video();

page.on('console', (msg) => {
  if (msg.type() === 'error') console.error(`[browser console] ${msg.text()}`);
});
page.on('pageerror', (error) => console.error(`[browser pageerror] ${error.message}`));

try {
  console.log(`Opening dashboard: ${BASE_URL}`);
  await page.goto(BASE_URL, { waitUntil: 'networkidle', timeout: 60_000 });
  await page.getByRole('heading', { name: 'Ascend Optimizer' }).waitFor({ timeout: 30_000 });
  await pause(3000);

  const amount = page.getByLabel('Decision Amount (0G)');
  const profile = page.getByLabel('Profile');
  const horizon = page.getByLabel('Holding Horizon (days)');
  const deadline = page.getByLabel('Optional Cash Deadline (days)');
  const mode = page.getByLabel('Evidence Mode');
  const optimize = page.getByRole('button', { name: 'Optimize Decision Sleeve' });

  await amount.fill('1000');
  await horizon.fill('90');
  await deadline.fill('');
  await mode.selectOption('SYNTHETIC_EVALUATION_ONLY');
  await pause(1200);

  // Show all three user profiles using the exact same amount and horizon.
  for (const profileName of ['Conservative', 'Balanced', 'Aggressive']) {
    console.log(`Recording synthetic profile: ${profileName}`);
    await profile.selectOption(profileName);
    await pause(1000);
    await submitAndWait(page, optimize, profileName, 'SYNTHETIC_EVALUATION_ONLY');
    await scrollTo(page, page.getByText('Policy-Aware Amount Optimizer', { exact: true }), 6000);
  }

  // Return to Balanced for the detailed walkthrough.
  console.log('Recording detailed Balanced walkthrough');
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'smooth' }));
  await pause(1200);
  await profile.selectOption('Balanced');
  await submitAndWait(page, optimize, 'Balanced', 'SYNTHETIC_EVALUATION_ONLY');

  await scrollTo(page, page.getByRole('heading', { name: 'Expected Economics' }), 5500);
  await scrollTo(page, page.getByRole('heading', { name: 'Risk & Policy' }), 5500);
  await scrollTo(page, page.getByRole('heading', { name: 'Liquidity & Exit Timing' }), 5000);
  await scrollTo(page, page.getByRole('heading', { name: 'Five Strategy Diagnostics' }), 3500);

  const jaine = page.locator('summary').filter({ hasText: 'Jaine' }).first();
  await jaine.click();
  await scrollTo(page, jaine, 6500);

  // Finish by demonstrating the canonical production fail-closed path.
  console.log('Recording production fail-closed result');
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'smooth' }));
  await pause(1500);
  await mode.selectOption('PRODUCTION');
  await profile.selectOption('Balanced');
  await pause(1000);
  await submitAndWait(page, optimize, 'Balanced', 'PRODUCTION');
  await scrollTo(page, page.getByRole('heading', { name: 'Production Evidence: Unresolved' }), 5500);
  await scrollTo(page, page.getByRole('heading', { name: 'Keep 100% Idle' }), 6000);
  await scrollTo(page, page.getByRole('heading', { name: 'Status & Readiness' }), 5500);

  await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'smooth' }));
  await pause(3500);
} catch (error) {
  console.error(error instanceof Error ? error.message : error);
  console.error('Visible page text at failure:');
  console.error((await page.locator('body').innerText()).slice(0, 6000));
  throw error;
} finally {
  await context.close();
  if (video) await video.saveAs(OUTPUT_FILE);
  await browser.close();
}

console.log(`Saved live browser recording to: ${OUTPUT_FILE}`);
