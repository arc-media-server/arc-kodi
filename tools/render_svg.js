// Renders SVG files to transparent PNGs at a given width, with Chromium (Playwright).
// Used by tools/make_media.py for the brand files; dev only.
//   node tools/render_svg.js <svg> <png> <width> [<svg> <png> <width> ...]
const fs = require('fs');
const { chromium } = require('playwright');

(async () => {
  const args = process.argv.slice(2);
  const browser = await chromium.launch();
  const page = await browser.newPage();
  for (let i = 0; i + 2 < args.length + 1; i += 3) {
    const [svg, png, width] = [args[i], args[i + 1], Number(args[i + 2])];
    const markup = fs.readFileSync(svg, 'utf8').replace('<svg ', '<svg width="100%" ');
    await page.setContent(`<html><body style="margin:0;background:transparent"><div id="m" style="width:${width}px;line-height:0">${markup}</div></body></html>`);
    await page.locator('#m').screenshot({ path: png, omitBackground: true });
  }
  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });
