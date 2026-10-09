#!/usr/bin/env node
/**
 * record_demo.mjs — record the roadbook's interactions as a frame sequence, for
 * the demo GIF in README.md.
 *
 * Drives a real browser over CDP rather than taking headless screenshots: the
 * drawer slide, the tab switch and the lightbox are CSS transitions, and they
 * have to be captured while they animate.
 *
 *   python3 -m http.server 8770 --bind 127.0.0.1   # from examples/.../out
 *   node scripts/record_demo.mjs http://localhost:8770/roadbook.html /tmp/frames
 *
 * Then assemble the frames into a GIF with Pillow — see README "Repo layout".
 * Requires a Chromium-family browser; honours $CHROME.
 */
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

const CHROME = process.env.CHROME ||
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const url = process.argv[2];
const outDir = process.argv[3] || '/tmp/gifframes';
const W = 390, H = 800;

fs.rmSync(outDir, { recursive: true, force: true });
fs.mkdirSync(outDir, { recursive: true });

const chrome = spawn(CHROME, ['--headless', '--disable-gpu', '--no-first-run',
  '--hide-scrollbars', '--remote-debugging-port=9455',
  `--window-size=${W + 120},${H}`, '--force-device-scale-factor=1',
  'about:blank'], { stdio: 'ignore' });

const sleep = ms => new Promise(r => setTimeout(r, ms));
let ws, id = 0;
const pend = new Map();
const send = (method, params = {}) => new Promise((res, rej) => {
  const i = ++id; pend.set(i, { res, rej });
  ws.send(JSON.stringify({ id: i, method, params }));
});
const evaluate = expression => send('Runtime.evaluate', { expression, awaitPromise: true });

let frame = 0;
const holds = [];
async function shot(holdMs) {
  const r = await send('Page.captureScreenshot', { format: 'png' });
  const name = String(frame++).padStart(3, '0');
  fs.writeFileSync(path.join(outDir, name + '.png'), Buffer.from(r.data, 'base64'));
  holds.push(holdMs);
}
/* Capture repeatedly while a CSS transition plays, so the slide is visible. */
async function burst(n, gapMs, holdMs) {
  for (let i = 0; i < n; i++) { await shot(holdMs); await sleep(gapMs); }
}

(async () => {
  let page = null;
  for (let i = 0; i < 40 && !page; i++) {
    await sleep(250);
    try {
      const list = await (await fetch('http://127.0.0.1:9455/json/list')).json();
      page = list.find(t => t.type === 'page');
    } catch {}
  }
  if (!page) { console.error('cannot reach Chrome'); process.exit(1); }

  ws = new WebSocket(page.webSocketDebuggerUrl);
  ws.onmessage = ev => {
    const m = JSON.parse(ev.data);
    if (m.id && pend.has(m.id)) {
      const { res, rej } = pend.get(m.id); pend.delete(m.id);
      m.error ? rej(new Error(JSON.stringify(m.error))) : res(m.result);
    }
  };
  await new Promise(r => (ws.onopen = r));
  await send('Page.enable');
  await send('Runtime.enable');
  // Constrain to a phone width: headless clamps windows to ~500px, so the page
  // is pinned to 390 and the frames are cropped to match.
  await send('Page.addScriptToEvaluateOnNewDocument', {
    source: `document.addEventListener('DOMContentLoaded',()=>{
      const s=document.createElement('style');
      s.textContent='html,body{width:${W}px!important;max-width:${W}px!important;overflow-x:hidden!important}';
      document.head.appendChild(s);});`
  });
  await send('Page.navigate', { url });
  await sleep(2500);

  // Hide the hero so the timeline is visible from the first frame.
  await evaluate(`document.querySelector('.hero').style.display='none';`);

  // 1. settle on a day with several tickets, scrolled into view
  await evaluate(`
    const d = document.querySelectorAll('.day')[7];
    window.scrollTo(0, d.offsetTop - 90);
  `);
  await sleep(500);
  await shot(1400);                                   // resting on the list

  // 2. open the drawer — two frames catch the 360ms slide in flight
  await evaluate(`document.querySelector('[data-open="7"]').click();`);
  await shot(90);
  await sleep(70);
  await shot(90);
  await sleep(340);
  await shot(1300);                                   // drawer settled

  // 3. switch to the transport tab
  await evaluate(`[...document.querySelectorAll('.dtab')]
    .find(b => b.textContent.includes('交通')).click();`);
  await sleep(250);
  await shot(1100);

  // 4. open a ticket full-screen
  await evaluate(`document.querySelector('.gitem').click();`);
  await sleep(500);
  await shot(1500);

  // 5. back out, and back to the list
  await evaluate(`document.getElementById('lbX').click();`);
  await sleep(350);
  await shot(700);
  await evaluate(`document.getElementById('dwX').click();`);
  await sleep(600);
  await shot(1600);                                   // loop back to the start

  fs.writeFileSync(path.join(outDir, 'holds.json'), JSON.stringify(holds));
  console.log(`  ${frame} frames -> ${outDir}`);
  ws.close(); chrome.kill();
  process.exit(0);
})();
