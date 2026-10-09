#!/usr/bin/env node
/**
 * encrypt_roadbook.mjs — wrap a generated roadbook in a password gate that is
 * actual encryption, not a JavaScript prompt.
 *
 * Why it matters: a roadbook carries live ticket QR codes. If you host it (the
 * obvious use — open it on your phone from anywhere), then on GitHub Pages the
 * site is public no matter how private the repository is; private Pages needs
 * GitHub Enterprise Cloud. A JavaScript "enter password" overlay would be pure
 * theatre, because the ticket data would still be sitting in the file in clear.
 *
 * So the whole payload — itinerary, lodging, and every ticket image — is
 * encrypted with AES-256-GCM under a key derived from the password via PBKDF2.
 * The file can be public; it is inert without the password.
 *
 * What this does NOT do: protect against a weak password. PBKDF2's 400k
 * iterations make each guess cost something, but a dictionary word is still a
 * dictionary word. Use a passphrase.
 *
 *   node scripts/encrypt_roadbook.mjs in.html -o out.html -p 'correct horse'
 *   RB_PASSWORD=... node scripts/encrypt_roadbook.mjs in.html -o out.html
 */

import fs from 'node:fs';
import zlib from 'node:zlib';
import crypto from 'node:crypto';

const ITER_DEFAULT = 400000;

function parseArgs(argv) {
  const a = { iter: ITER_DEFAULT };
  for (let i = 2; i < argv.length; i++) {
    const k = argv[i];
    if (k === '-o' || k === '--out') a.out = argv[++i];
    else if (k === '-p' || k === '--password') a.password = argv[++i];
    else if (k === '--iter') a.iter = parseInt(argv[++i], 10);
    else if (k === '--title') a.title = argv[++i];
    else if (!a.input) a.input = k;
    else throw new Error(`unexpected argument: ${k}`);
  }
  a.password = a.password || process.env.RB_PASSWORD;
  return a;
}

const LOCK_CSS = `
body:not(.ok) > *:not(.lock){display:none!important}
.lock{position:fixed;inset:0;z-index:500;display:grid;place-items:center;padding:24px;
  background:linear-gradient(150deg,#0f766e 0%,#1d4ed8 58%,#3730a3 100%)}
.lock::after{content:"";position:absolute;inset:0;pointer-events:none;
  background:radial-gradient(680px 300px at 80% -10%,rgba(255,255,255,.26),transparent 62%)}
.lock-card{position:relative;z-index:1;width:100%;max-width:330px;text-align:center;color:#fff;
  background:rgba(255,255,255,.13);border:1px solid rgba(255,255,255,.25);
  border-radius:22px;padding:30px 24px 26px;backdrop-filter:blur(14px);
  box-shadow:0 20px 60px -18px rgba(0,0,0,.55)}
.lock-card.shake{animation:shk .42s}
@keyframes shk{10%,90%{transform:translateX(-3px)}20%,80%{transform:translateX(5px)}
  30%,50%,70%{transform:translateX(-8px)}40%,60%{transform:translateX(8px)}}
.lock-ico{font-size:38px;line-height:1;margin-bottom:12px}
.lock-card h2{margin:0 0 6px;font-size:18px;font-weight:800}
.lock-sub{margin:0 0 20px;font-size:12.5px;opacity:.85;line-height:1.5}
.lock-card input{width:100%;padding:14px 16px;border-radius:13px;font-size:16px;
  border:1px solid rgba(255,255,255,.35);background:rgba(255,255,255,.16);color:#fff;
  outline:none;text-align:center;letter-spacing:3px;-webkit-appearance:none;appearance:none}
.lock-card input::placeholder{color:rgba(255,255,255,.55);letter-spacing:0}
.lock-card input:focus{border-color:#fff;background:rgba(255,255,255,.24)}
.lock-card button{width:100%;margin-top:12px;padding:14px;border-radius:13px;font-size:15px;
  font-weight:800;background:#fff;color:#1d4ed8;transition:.18s}
.lock-card button:active{transform:scale(.98)}
.lock-card button:disabled{opacity:.6}
.lock-err{margin:12px 0 0;font-size:12.5px;font-weight:700;color:#fecaca;min-height:16px}
.lock-tip{margin:14px 0 0;font-size:10.5px;opacity:.6;line-height:1.5}
`;

const buildLockHtml = (title) => `
<div class="lock" id="lock">
  <div class="lock-card" id="lockCard">
    <div class="lock-ico">🔒</div>
    <h2>${title}</h2>
    <p class="lock-sub">内容已加密 · 请输入密码查看<br>行程安排与全部票据</p>
    <input id="pw" type="password" placeholder="密码" autocomplete="off"
           autocapitalize="off" autocorrect="off" spellcheck="false">
    <button id="unlockBtn">解 锁</button>
    <p class="lock-err" id="lockErr"></p>
    <p class="lock-tip">票据已加密存储，密码不正确无法读取</p>
  </div>
</div>
`;

const CRYPTO_JS = (salt, iv, iter) => `
const SALT = b64bytes("${salt}");
const IV   = b64bytes("${iv}");
const ITER = ${iter};
function b64bytes(s){
  const bin = atob(s), u = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i);
  return u;
}
async function deriveKey(pw){
  const base = await crypto.subtle.importKey(
    'raw', new TextEncoder().encode(pw), 'PBKDF2', false, ['deriveKey']);
  return crypto.subtle.deriveKey(
    { name:'PBKDF2', salt:SALT, iterations:ITER, hash:'SHA-256' },
    base, { name:'AES-GCM', length:256 }, false, ['decrypt']);
}
async function decryptAll(key){
  const ct = b64bytes(document.getElementById('ct').textContent.trim());
  const pt = await crypto.subtle.decrypt({ name:'AES-GCM', iv:IV }, key, ct);
  // gzip first, so the base64 payload doesn't pay the 33% expansion twice.
  const stream = new Blob([pt]).stream().pipeThrough(new DecompressionStream('gzip'));
  return JSON.parse(await new Response(stream).text());
}
`;

const UNLOCK_JS = `
(function(){
  const card = document.getElementById('lockCard');
  const pwEl = document.getElementById('pw');
  const btn  = document.getElementById('unlockBtn');
  const err  = document.getElementById('lockErr');
  let busy = false;

  async function tryUnlock(){
    const pw = pwEl.value;
    if (!pw || busy) return;
    busy = true; err.textContent = '';
    btn.disabled = true; btn.textContent = '解密中…';
    try {
      const key = await deriveKey(pw);
      const payload = await decryptAll(key);
      ASSETS = payload.assets;
      TRIP = payload.data;
      document.body.classList.add('ok');
      document.getElementById('lock').remove();
      boot();
    } catch (e) {
      err.textContent = '密码不正确，请重试';
      btn.disabled = false; btn.textContent = '解 锁';
      pwEl.value = ''; pwEl.focus();
      card.classList.add('shake');
      setTimeout(() => card.classList.remove('shake'), 460);
      busy = false;
    }
  }
  btn.addEventListener('click', tryUnlock);
  pwEl.addEventListener('keydown', e => { if (e.key === 'Enter') tryUnlock(); });
  setTimeout(() => pwEl.focus(), 250);
})();
`;

function main() {
  const a = parseArgs(process.argv);
  if (!a.input) {
    console.error('usage: node scripts/encrypt_roadbook.mjs <roadbook.html> -o <out.html> [-p PASSWORD] [--iter N]');
    return 2;
  }
  if (!fs.existsSync(a.input)) {
    console.error(`error: input not found: ${a.input}`);
    return 1;
  }
  if (!a.password) {
    console.error('error: no password. Pass -p, or set RB_PASSWORD, or let build.py generate one.');
    return 2;
  }
  if (!a.out) a.out = a.input.replace(/\.html$/, '') + '.enc.html';

  const src = fs.readFileSync(a.input, 'utf8');

  // The roadbook stores its payload as two top-level `const` literals. Pull them
  // out so they can be encrypted, and leave the rendering code in the clear —
  // it is just a viewer and contains nothing worth hiding.
  const grab = (name) => {
    const m = new RegExp(`const ${name} = ([\\s\\S]*?);\\n`).exec(src);
    if (!m) throw new Error(`could not find \`const ${name}\` in ${a.input}`);
    return m[1];
  };
  let assetsSrc, tripSrc;
  try {
    assetsSrc = grab('ASSETS');
    tripSrc = grab('TRIP');
  } catch (e) {
    console.error(`error: ${e.message}\n` +
      '       (encryption expects a roadbook generated by gen_roadbook.py)');
    return 1;
  }

  const payload = Buffer.from(JSON.stringify({
    assets: JSON.parse(assetsSrc),
    data: JSON.parse(tripSrc),
  }), 'utf8');

  const gz = zlib.gzipSync(payload, { level: 9 });
  const salt = crypto.randomBytes(16);
  const iv = crypto.randomBytes(12);
  const key = crypto.pbkdf2Sync(a.password, salt, a.iter, 32, 'sha256');
  const cipher = crypto.createCipheriv('aes-256-gcm', key, iv);
  const ct = Buffer.concat([cipher.update(gz), cipher.final(), cipher.getAuthTag()]);

  const title = a.title || (JSON.parse(tripSrc).hero?.title ?? '路书').replace(/^[^\p{L}]*/u, '');

  let out = src;
  // Hide the app until unlocked, and put the lock screen on top.
  out = out.replace('</style>', LOCK_CSS + '</style>');
  out = out.replace(/<body>/, '<body>' + buildLockHtml(title));
  // Replace the two plaintext payloads with the decryptor, and wrap the
  // existing render code so it runs only after a successful unlock.
  // Both literals are emitted one-per-line by json.dumps, so `;\n` terminates
  // each of them unambiguously.
  const payloadRe = /const ASSETS = [\s\S]*?;\nconst TRIP = [\s\S]*?;\n/;
  if (!payloadRe.test(out)) {
    console.error('error: could not locate the ASSETS/TRIP payload block to replace');
    return 1;
  }
  out = out.replace(payloadRe,
    CRYPTO_JS(salt.toString('base64'), iv.toString('base64'), a.iter) +
    '\nlet ASSETS = null, TRIP = null;\nfunction boot(){');
  out = out.replace('</script>\n</body>',
    '}\n' + UNLOCK_JS + '\n</script>\n' +
    '<script type="application/octet-stream" id="ct">' + ct.toString('base64') + '</script>\n</body>');

  // Paranoia: none of the plaintext payload may survive into the output.
  for (const needle of ['data:image/jpeg;base64', 'Via dei ', '"lodging"']) {
    if (out.includes(needle)) {
      console.error(`error: plaintext leak detected (${needle}) — refusing to write`);
      return 1;
    }
  }

  fs.writeFileSync(a.out, out);
  console.log(`  ${a.out}  (${(fs.statSync(a.out).size / 1048576).toFixed(1)} MB, ` +
              `PBKDF2 ${a.iter.toLocaleString()} iterations)`);
  return 0;
}

process.exit(main());
