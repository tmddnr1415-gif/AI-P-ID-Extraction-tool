// UI features against a mocked API: "/" prompt picker with {{variables}}, regenerate, edit & resend,
// chat history persisted in IndexedDB across reloads, projects, table copy.
//   NODE_PATH=$(npm root -g) node ic-expert/dev/test_ui.mjs
import { createRequire } from 'node:module';
import path from 'node:path'; import url from 'node:url';

const { chromium } = createRequire(import.meta.url)('playwright');
const file = path.resolve(path.dirname(url.fileURLToPath(import.meta.url)), '../index.html');
const sse = (text) => [
  { type: 'message_start', message: { usage: { input_tokens: 5 } } },
  { type: 'content_block_start', index: 0, content_block: { type: 'text', text: '' } },
  { type: 'content_block_delta', index: 0, delta: { type: 'text_delta', text } },
  { type: 'content_block_stop', index: 0 },
  { type: 'message_delta', delta: { stop_reason: 'end_turn' }, usage: { output_tokens: 3 } },
].map((e) => `event: ${e.type}\ndata: ${JSON.stringify(e)}\n\n`).join('');

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1300, height: 900 } });
const page = await ctx.newPage();
const errors = []; page.on('pageerror', (e) => errors.push(String(e)));
const bodies = []; let n = 0;
await page.route('https://api.anthropic.com/**', (r) => {
  bodies.push(JSON.parse(r.request().postData())); n++;
  r.fulfill({ status: 200, body: sse(`answer ${n}\n\n| a | b |\n|---|---|\n| 1 | 2 |`), headers: { 'content-type': 'text/event-stream', 'access-control-allow-origin': '*' } });
});
// a static http origin so IndexedDB persists across reloads
await page.goto('file://' + file);
await page.evaluate(() => localStorage.setItem('icx.key', 'sk-test'));
const done = (k) => page.waitForFunction((kk) => document.querySelectorAll('.msg.assistant .acts').length >= kk && !document.getElementById('btn-send').disabled, k, { timeout: 8000 });
const ok = []; const check = (name, c) => { ok.push(!!c); console.log(c ? '✓' : '✗', name); };

// 1. "/" picker → prompt with variables
await page.click('#input'); await page.keyboard.type('/thermo');
check('picker opens on "/"', await page.isVisible('#picker'));
await page.keyboard.press('Enter');
check('variables dialog opens', await page.isVisible('#dlg-vars'));
const fields = await page.$$('#dv-fields input');
check('6 variables asked', fields.length === 6);
await fields[0].fill('8 m/s');
await page.click('#dv-ok');
const val = await page.inputValue('#input');
check('prompt inserted with value and placeholders', val.includes('velocity 8 m/s') && val.includes('[fluid]') && !val.includes('/thermo'));

// 2. send, then regenerate
await page.click('#btn-send'); await done(1);
check('answer rendered with table toolbar', (await page.textContent('.msg.assistant .body')).includes('answer 1') && await page.isVisible('.blk-bar'));
await page.hover('.msg.assistant'); await page.click('.msg.assistant .act[title="Regenerate"]'); await done(1);
check('regenerate replaced the answer', (await page.textContent('.msg.assistant .body')).includes('answer 2') && (await page.$$('.msg.assistant')).length === 1);
check('regenerate resent the same single user turn', bodies[1].messages.length === 1 && bodies[1].messages[0].role === 'user');

// 3. second turn, then edit the first question
await page.fill('#input', 'second question'); await page.click('#btn-send'); await done(2);
check('two turns', (await page.$$('.msg.assistant')).length === 2);
await page.hover('.msg.user >> nth=0'); await page.click('.msg.user >> nth=0 >> .act[title="Edit and resend"]');
await page.fill('textarea.edit', 'edited first question');
await page.click('.msg.user >> nth=0 >> text=Save & submit'); await done(1);
const last = bodies.at(-1);
check('edit truncated history and resent', last.messages.length === 1 && last.messages[0].content.at(-1).text === 'edited first question' && (await page.$$('.msg.assistant')).length === 1);

// 4. history survives reload
const title = await page.textContent('#chat-title');
await page.reload(); await page.waitForTimeout(600);
const items = await page.$$eval('#chat-list .it-title', (els) => els.map((e) => e.textContent));
check('chat listed after reload', items.length === 1 && items[0] === title);
await page.click('#chat-list .item'); await page.waitForTimeout(200);
check('reopened chat shows its turn', (await page.$$('.msg.user')).length === 1 && (await page.textContent('.msg.user')).includes('edited first question'));

// 5. projects drive the context
await page.click('.sw-btn[data-tab="projects"]'); await page.click('#btn-new-project');
await page.fill('#ctx-name', 'NFE LNG'); await page.selectOption('#ctx-client', { label: 'QatarEnergy / QatarEnergy LNG' });
await page.click('.sw-btn[data-tab="chats"]'); await page.click('#btn-new');
await page.fill('#input', 'q'); await page.click('#btn-send'); await done(1);
check('new project context sent', /QatarEnergy/.test(bodies.at(-1).system[1].text) && /NFE LNG/.test(bodies.at(-1).system[1].text));
check('two chats in history', (await page.$$('#chat-list .item')).length === 2);

// 6. knowledge viewer
await page.click('.sw-btn[data-tab="knowledge"]');
const kb = await page.$$('#kb-list .item');
if (kb.length) { await kb[0].click(); check('knowledge file opens', await page.isVisible('#dlg-kb')); await page.click('#dk-close'); }
check('no page errors', errors.length === 0);
if (process.env.SHOT) await page.screenshot({ path: process.env.SHOT });
await browser.close();
if (errors.length) console.log(errors);
process.exit(ok.every(Boolean) ? 0 : 1);
