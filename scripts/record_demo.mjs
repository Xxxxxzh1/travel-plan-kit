#!/usr/bin/env node
/**
 * record_demo.mjs — record the roadbook's interactions as a frame sequence, for
 * the demo GIF in README.md.
 *
 * Two things this gets right that a naive screen recording does not:
 *
 * 1. **The viewport is set via CDP `Emulation.setDeviceMetricsOverride`, not
 *    `--window-size`.** Headless Chrome clamps and then shrinks the window
 *    (asking for 800px of height yields a 713px viewport), so the frames come
 *    out cropped. Device metrics give an exact 390x844 phone.
 * 2. **It drives a real browser rather than taking static screenshots.** The
 *    drawer slide, the tab switch and the lightbox are CSS transitions; they
 *    have to be captured while they animate.
 *
 *   cd examples/italy-switzerland/out && python3 -m http.server 8770 --bind 127.0.0.1 &
 *   node scripts/record_demo.mjs http://localhost:8770/roadbook.html /tmp/frames
 *
 * Then assemble the PNGs in /tmp/frames into a GIF with Pillow.
 * Requires a Chromium-family browser; honours $CHROME.
 */

import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

const CHROME = process.env.CHROME ||
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const url = process.argv[2];
const outDir = process.argv[3] || '/tmp/frames';

// A real phone viewport. 390x844 is the logical size of an iPhone 14/15.
const VW = 390, VH = 844, DSF = 2;
// Which day to demo: needs more than one ticket category, so the tabs show.
const DAY_INDEX = 7;

fs.rmSync(outDir, { recursive: true, force: true });
fs.mkdirSync(outDir, { recursive: true });

const chrome = spawn(CHROME, ['--headless', '--disable-gpu', '--no-first-run',
  '--hide-scrollbars', '--remote-debugging-port=9466', 'about:blank'],
  { stdio: 'ignore' });

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
async function shot(holdMs = 0, label = '') {
  const r = await send('Page.captureScreenshot', { format: 'png' });
  const name = String(frame).padStart(3, '0') + (label ? '-' + label : '');
  fs.writeFileSync(path.join(outDir, name + '.png'), Buffer.from(r.data, 'base64'));
  holds.push(holdMs);
  frame++;
}

(async () => {
  let page = null;
  for (let i = 0; i < 40 && !page; i++) {
    await sleep(250);
    try {
      const list = await (await fetch('http://127.0.0.1:9466/json/list')).json();
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
  // Exact phone viewport — no CSS width injection needed, nothing gets clamped.
  await send('Emulation.setDeviceMetricsOverride', {
    width: VW, height: VH, deviceScaleFactor: DSF, mobile: false,
  });
  await send('Page.navigate', { url });
  await sleep(2600);

  const probe = await send('Runtime.evaluate', {
    expression: 'JSON.stringify({w:innerWidth,h:innerHeight,dpr:devicePixelRatio})',
    returnByValue: true });
  console.log('  viewport:', probe.result.value);

  // The hero is tall; hide it so the timeline is the subject of the first frame.
  await evaluate(`document.querySelector('.hero').style.display='none';`);
  await evaluate(`
    const d = document.querySelectorAll('.day')[${DAY_INDEX}];
    window.scrollTo(0, d.offsetTop - 70);
  `);
  await sleep(600);

  await shot(1600, 'list');                       // 1. resting on the day list

  // The drawer slides in over 360ms — shorter than a CDP round-trip, so naive
  // capture only ever sees the finished state. Stretch the transition for the
  // recording and sample inside it; the GIF's own frame delays restore the
  // original pacing, so it still reads as a quick slide.
  await evaluate(`document.getElementById('dw').style.transitionDuration='3s';`);
  await evaluate(`document.querySelector('[data-open="${DAY_INDEX}"]').click();`);
  await sleep(500);
  await shot(140, 'slide1');                      // 2. drawer sliding up
  await sleep(700);
  await shot(140, 'slide2');                      // 3. still sliding
  await sleep(750);
  await shot(140, 'slide3');                      // 4. nearly there
  await sleep(1600);                              // let it settle
  await evaluate(`document.getElementById('dw').style.transitionDuration='';`);
  await shot(1500, 'drawer');                     // 5. drawer settled

  await evaluate(`[...document.querySelectorAll('.dtab')]
    .find(b => b.textContent.includes('交通')).click();`);
  await sleep(300);
  await shot(1400, 'tab');                        // 5. transport tab, tickets visible

  await evaluate(`document.querySelector('.gitem').click();`);
  await sleep(600);
  await shot(1900, 'lightbox');                   // 6. ticket full-screen

  await evaluate(`document.getElementById('lbX').click();`);
  await sleep(450);
  await shot(900, 'back');                        // 7. back to the drawer

  await evaluate(`document.getElementById('dw').style.transitionDuration='2s';`);
  await evaluate(`document.getElementById('dwX').click();`);
  await sleep(350);
  await shot(140, 'close1');                      // 9. drawer sliding away
  await sleep(900);
  await shot(140, 'close2');
  await sleep(1400);
  await evaluate(`document.getElementById('dw').style.transitionDuration='';`);
  await shot(900, 'list2');                       // 10. back on the list
  await evaluate(`window.scrollTo(0, document.querySelectorAll('.day')[${DAY_INDEX}].offsetTop - 70);`);
  await sleep(300);
  await shot(1400, 'loop');                       // 11. loop point — matches frame 1

  fs.writeFileSync(path.join(outDir, 'holds.json'), JSON.stringify(holds));
  console.log(`  ${frame} frames -> ${outDir}`);
  ws.close(); chrome.kill();
  process.exit(0);
})();
