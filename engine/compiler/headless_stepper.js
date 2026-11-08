/**
 * Headless Chromium Frame Stepper & Pre-Render Validator
 * Uses Puppeteer with Direct3D 11 hardware acceleration on Windows.
 */

import puppeteer from 'puppeteer';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';

const args = process.argv.slice(2);
const options = {
  mode: 'lint', // 'lint', 'snapshot', 'stream'
  input: '',
  output: '',
  duration: 5.0,
  fps: 60,
  width: 3840,
  height: 2160,
  time: 0.0
};

for (let i = 0; i < args.length; i++) {
  if (args[i] === '--mode') options.mode = args[++i];
  else if (args[i] === '--input') options.input = args[++i];
  else if (args[i] === '--output') options.output = args[++i];
  else if (args[i] === '--duration') options.duration = parseFloat(args[++i]);
  else if (args[i] === '--fps') options.fps = parseInt(args[++i], 10);
  else if (args[i] === '--width') options.width = parseInt(args[++i], 10);
  else if (args[i] === '--height') options.height = parseInt(args[++i], 10);
  else if (args[i] === '--time') options.time = parseFloat(args[++i]);
}

if (!options.input) {
  console.error(JSON.stringify({ error: 'Missing --input argument' }));
  process.exit(1);
}

let rawInput = options.input;
let suffix = '';
if (rawInput.includes('?')) {
  const parts = rawInput.split('?');
  rawInput = parts[0];
  suffix = '?' + parts.slice(1).join('?');
} else if (rawInput.includes('#')) {
  const parts = rawInput.split('#');
  rawInput = parts[0];
  suffix = '#' + parts.slice(1).join('#');
}
const inputPath = path.resolve(rawInput);
const fileUrl = 'file:///' + inputPath.replace(/\\/g, '/') + suffix;

async function run() {
  const browser = await puppeteer.launch({
    headless: 'new',
    args: [
      `--window-size=${options.width},${options.height}`,
      '--use-gl=angle',
      '--use-angle=d3d11',
      '--enable-gpu-rasterization',
      '--ignore-gpu-blocklist',
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--allow-file-access-from-files',
      '--disable-web-security'
    ],
    defaultViewport: {
      width: options.width,
      height: options.height,
      deviceScaleFactor: 1
    }
  });

  const page = await browser.newPage();
  const consoleErrors = [];
  const consoleWarnings = [];

  page.on('console', (msg) => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
    else if (msg.type() === 'warning') consoleWarnings.push(msg.text());
  });

  page.on('pageerror', (err) => {
    consoleErrors.push(err.toString());
  });

  try {
    await page.goto(fileUrl, { waitUntil: 'load', timeout: 30000 });

    // Await readiness contract
    await page.waitForFunction(
      () => typeof window.renderFrame === 'function' && window.__SCENE_READY__,
      { timeout: 15000 }
    );

    // MODE 1: PRE-RENDER LINT & SANITY CHECK
    if (options.mode === 'lint') {
      // Step to frame 0
      await page.evaluate(() => window.renderFrame(0.0));
      await new Promise((r) => setTimeout(r, 100));

      const screenshotBuf = await page.screenshot({ type: 'png', omitBackground: false });
      
      // Calculate luminance sample from center pixels
      let nonZero = 0;
      for (let i = 0; i < screenshotBuf.length; i += 16) {
        if (screenshotBuf[i] > 10) nonZero++;
      }

      const hasContent = nonZero > 100;
      const result = {
        valid: consoleErrors.length === 0 && hasContent,
        errors: consoleErrors,
        warnings: consoleWarnings,
        hasNonBlackContent: hasContent,
        width: options.width,
        height: options.height
      };

      console.log(JSON.stringify(result));
      await browser.close();
      process.exit(result.valid ? 0 : 2);
    }

    // MODE 2: SINGLE KEYFRAME SNAPSHOT (FOR THUMBNAILS & INSPECTION)
    if (options.mode === 'snapshot' || options.mode === 'frame') {
      await page.evaluate((t) => window.renderFrame(t), options.time);
      await new Promise((r) => setTimeout(r, 50));
      
      const outPath = path.resolve(options.output || 'snapshot.png');
      await page.screenshot({ path: outPath, type: 'png' });
      
      console.log(JSON.stringify({ status: 'OK', snapshot: outPath, time: options.time }));
      await browser.close();
      process.exit(0);
    }

    // MODE 3: DIRECT MEMORY-STREAMING TO STDOUT (FOR NVENC ENCODER)
    if (options.mode === 'stream') {
      const totalFrames = Math.ceil(options.duration * options.fps);
      const frameDelta = 1.0 / options.fps;

      for (let f = 0; f < totalFrames; f++) {
        const currentTime = f * frameDelta;
        await page.evaluate((t) => window.renderFrame(t), currentTime);

        // Capture raw screenshot buffer and write to stdout
        const buffer = await page.screenshot({ type: 'png' });
        
        // Handle backpressure so V8 memory does not exhaust on long scenes
        const canWrite = process.stdout.write(buffer);
        if (!canWrite) {
          await new Promise((resolve) => process.stdout.once('drain', resolve));
        }

        if (f % 150 === 0 || f === totalFrames - 1) {
          process.stderr.write(`[Stepper] Frame ${f}/${totalFrames} (${((f / totalFrames) * 100).toFixed(1)}%)\n`);
        }
      }

      await browser.close();
      process.exit(0);
    }

    console.error(JSON.stringify({ error: `Invalid mode: ${options.mode}. Expected 'lint', 'snapshot', 'frame', or 'stream'.` }));
    await browser.close();
    process.exit(1);

  } catch (err) {
    console.error(JSON.stringify({ error: err.message, stack: err.stack, pageErrors: consoleErrors }));
    await browser.close();
    process.exit(1);
  }
}

run();
