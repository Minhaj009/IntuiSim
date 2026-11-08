/**
 * SVG to High-Resolution PNG Rasterizer
 * Uses Puppeteer to render vector SVGs at arbitrary pixel resolutions with transparency.
 */

import puppeteer from 'puppeteer';
import fs from 'fs';
import path from 'path';

const args = process.argv.slice(2);
const svgPath = path.resolve(args[0]);
const outPngPath = path.resolve(args[1]);
const width = parseInt(args[2] || '512', 10);
const height = parseInt(args[3] || '512', 10);

async function rasterize() {
  const svgContent = fs.readFileSync(svgPath, 'utf8');
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-web-security']
  });

  const page = await browser.newPage();
  await page.setViewport({ width, height, deviceScaleFactor: 1 });
  
  // HTML wrapper with SVG scaled to 100% width and height
  const html = `<!DOCTYPE html>
<html>
<head>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    html, body { width: 100%; height: 100%; overflow: hidden; background: transparent; }
    svg { width: 100%; height: 100%; display: block; }
  </style>
</head>
<body>
  ${svgContent}
</body>
</html>`;

  await page.setContent(html, { waitUntil: 'load' });
  await page.screenshot({ path: outPngPath, omitBackground: true, type: 'png' });
  await browser.close();
  console.log(`Rasterized ${svgPath} -> ${outPngPath} (${width}x${height})`);
}

rasterize().catch((err) => {
  console.error('Rasterization failed:', err);
  process.exit(1);
});
