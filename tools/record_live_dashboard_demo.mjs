import { chromium } from 'playwright';
import fs from 'node:fs/promises';
import path from 'node:path';

const BASE_URL = process.env.DEMO_URL ?? 'http://127.0.0.1:3000';
const OUTPUT_DIR = path.resolve(process.env.DEMO_OUTPUT_DIR ?? 'demo-output');
const OUTPUT_FILE = path.join(OUTPUT_DIR, 'ascend-optimizer-live-demo-captioned.webm');

const pause = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function showCaption(page, text, holdMs = 2600) {
  await page.evaluate((captionText) => {
    document.getElementById('__demo_caption__')?.remove();
    const caption = document.createElement('div');
    caption.id = '__demo_caption__';
    caption.textContent = captionText;
    Object.assign(caption.style, {
      position: 'fixed',
      left: '50%',
      bottom: '34px',
      transform: 'translateX(-50%)',
      zIndex: '2147483647',
      maxWidth: '86vw',
      padding: '12px 22px',
      borderRadius: '10px',
      background: 'rgba(17, 24, 39, 0.90)',
      color: '#ffffff',
      fontFamily: 'Arial, Helvetica, sans-serif',
      fontSize: '24px',
      fontWeight: '700',
      lineHeight: '1.25',
      textAlign: 'center',
      letterSpacing: '0.01em',
      boxShadow: '0 4px 18px rgba(0,0,0,0.28)',
      pointerEvents: 'none',
    });
    document.body.appendChild(caption);
  }, text);
  await pause(holdMs);
  await page.evaluate(() => document.getElementById('__demo_caption__')?.remove());
  await pause(350);
}

async function submitAndWait(page, optimize, profileName, modeName) {
  await optimize.click();
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
  await pause(1800);
  await showCaption(page, 'Ascend Optimizer — Live Prototype Demo', 3000);

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
  await showCaption(page, 'Common Input: 1,000 0G · 90 Days · Synthetic Evaluation', 2800);

  for (const profileName of ['Conservative', 'Balanced', 'Aggressive']) {
    console.log(`Recording synthetic profile: ${profileName}`);
    await profile.selectOption(profileName);
    await showCaption(page, `Synthetic Evaluation — ${profileName} Profile`, 2400);
    await submitAndWait(page, optimize, profileName, 'SYNTHETIC_EVALUATION_ONLY');
    await scrollTo(page, page.getByText('Policy-Aware Amount Optimizer', { exact: true }), 5000);
  }

  console.log('Recording detailed Balanced walkthrough');
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'smooth' }));
  await pause(1200);
  await profile.selectOption('Balanced');
  await showCaption(page, 'Balanced Profile — Detailed Walkthrough', 2400);
  await submitAndWait(page, optimize, 'Balanced', 'SYNTHETIC_EVALUATION_ONLY');

  await scrollTo(page, page.getByRole('heading', { name: 'Expected Economics' }), 800);
  await showCaption(page, 'Balanced Profile — Expected Economics', 2800);
  await pause(1800);

  await scrollTo(page, page.getByRole('heading', { name: 'Risk & Policy' }), 800);
  await showCaption(page, 'Balanced Profile — Risk & Policy', 2800);
  await pause(1800);

  await scrollTo(page, page.getByRole('heading', { name: 'Liquidity & Exit Timing' }), 800);
  await showCaption(page, 'Balanced Profile — Liquidity & Exit Timing', 2800);
  await pause(1600);

  await scrollTo(page, page.getByRole('heading', { name: 'Five Strategy Diagnostics' }), 800);
  await showCaption(page, 'Five Strategy Diagnostics', 2400);

  const jaine = page.locator('summary').filter({ hasText: 'Jaine' }).first();
  await jaine.click();
  await scrollTo(page, jaine, 800);
  await showCaption(page, 'Jaine LP — Strategy Diagnostics', 3000);
  await pause(2300);

  console.log('Recording production fail-closed result');
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'smooth' }));
  await pause(1200);
  await mode.selectOption('PRODUCTION');
  await profile.selectOption('Balanced');
  await showCaption(page, 'Production Evidence — Fail-Closed Mode', 2800);
  await submitAndWait(page, optimize, 'Balanced', 'PRODUCTION');

  await scrollTo(page, page.getByRole('heading', { name: 'Production Evidence: Unresolved' }), 700);
  await showCaption(page, 'Production Evidence Unresolved', 2600);

  await scrollTo(page, page.getByRole('heading', { name: 'Keep 100% Idle' }), 700);
  await showCaption(page, 'Production Result — Keep 100% Idle', 3000);
  await pause(2000);

  await scrollTo(page, page.getByRole('heading', { name: 'Status & Readiness' }), 700);
  await showCaption(page, 'Status & Readiness — Execution Not Established', 3000);
  await pause(1700);

  await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'smooth' }));
  await pause(1200);
  await showCaption(page, 'End of Live Demo', 2600);
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

console.log(`Saved captioned live browser recording to: ${OUTPUT_FILE}`);
