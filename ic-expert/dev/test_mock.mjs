// Headless test of the chat against a mocked Messages API stream:
// thinking + web search (server_tool_use / web_search_tool_result) + cited text, a pause_turn resume,
// and a second turn that must send the first assistant turn back unchanged.
//   NODE_PATH=$(npm root -g) node ic-expert/dev/test_mock.mjs
import { createRequire } from 'node:module';
import path from 'node:path'; import url from 'node:url';

const { chromium } = createRequire(import.meta.url)('playwright');
const html = path.resolve(path.dirname(url.fileURLToPath(import.meta.url)), '../index.html');

const sse = (events) => events.map((e) => `event: ${e.type}\ndata: ${JSON.stringify(e)}\n\n`).join('');
const R1 = sse([
  { type: 'message_start', message: { usage: { input_tokens: 50, cache_creation_input_tokens: 9000 } } },
  { type: 'content_block_start', index: 0, content_block: { type: 'thinking', thinking: '' } },
  { type: 'content_block_delta', index: 0, delta: { type: 'signature_delta', signature: 'sig-1' } },
  { type: 'content_block_stop', index: 0 },
  { type: 'content_block_start', index: 1, content_block: { type: 'server_tool_use', id: 'srvtoolu_1', name: 'web_search', input: {} } },
  { type: 'content_block_delta', index: 1, delta: { type: 'input_json_delta', partial_json: '{"query":"NAMUR NE 43' } },
  { type: 'content_block_delta', index: 1, delta: { type: 'input_json_delta', partial_json: ' failure current"}' } },
  { type: 'content_block_stop', index: 1 },
  { type: 'content_block_start', index: 2, content_block: { type: 'web_search_tool_result', tool_use_id: 'srvtoolu_1', content: [{ type: 'web_search_result', url: 'https://example.org/ne43', title: 'NE 43 explained', encrypted_content: 'x' }] } },
  { type: 'content_block_stop', index: 2 },
  { type: 'message_delta', delta: { stop_reason: 'pause_turn' }, usage: { output_tokens: 20 } },
]);
const R2 = sse([
  { type: 'message_start', message: { usage: { input_tokens: 60, cache_read_input_tokens: 9000 } } },
  { type: 'content_block_start', index: 0, content_block: { type: 'text', text: '' } },
  { type: 'content_block_delta', index: 0, delta: { type: 'text_delta', text: '**Answer** — set the failure alarm at ≤3.6 mA.\n\n| # | Item | Opinion |\n|---|---|---|\n| 1 | Low | 3.6 mA |\n' } },
  { type: 'content_block_delta', index: 0, delta: { type: 'citations_delta', citation: { type: 'web_search_result_location', url: 'https://example.org/ne43', title: 'NE 43 explained', cited_text: '≤3.6 mA', encrypted_index: 'e' } } },
  { type: 'content_block_delta', index: 0, delta: { type: 'text_delta', text: '\n- Basis [KB-01 §NAMUR NE 43]' } },
  { type: 'content_block_stop', index: 0 },
  { type: 'message_delta', delta: { stop_reason: 'end_turn' }, usage: { output_tokens: 80 } },
]);
const R3 = sse([
  { type: 'message_start', message: { usage: { input_tokens: 10 } } },
  { type: 'content_block_start', index: 0, content_block: { type: 'text', text: '' } },
  { type: 'content_block_delta', index: 0, delta: { type: 'text_delta', text: '네, 21 mA 이상도 고장입니다.' } },
  { type: 'content_block_stop', index: 0 },
  { type: 'message_delta', delta: { stop_reason: 'end_turn' }, usage: { output_tokens: 9 } },
]);

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1300, height: 900 } });
const errors = []; page.on('pageerror', (e) => errors.push(String(e)));
const bodies = []; const replies = [R1, R2, R3];
await page.route('https://api.anthropic.com/**', (r) => {
  bodies.push(JSON.parse(r.request().postData()));
  r.fulfill({ status: 200, body: replies.shift(), headers: { 'content-type': 'text/event-stream', 'access-control-allow-origin': '*' } });
});
await page.goto('file://' + html);
await page.evaluate(() => localStorage.setItem('icx.key', 'sk-test'));
await page.fill('#input', 'What failure current does NE 43 define?');
await page.click('#btn-send');
await page.waitForFunction(() => document.getElementById('status').textContent.startsWith('Done'), null, { timeout: 10000 });
await page.fill('#input', '21 mA 이상은?');
await page.click('#btn-send');
await page.waitForFunction(() => document.querySelectorAll('.msg.assistant').length === 2
  && document.getElementById('status').textContent.startsWith('Done'), null, { timeout: 10000 });

const ok = [];
const check = (name, cond) => { ok.push(!!cond); console.log(cond ? '✓' : '✗', name); };
check('3 API calls (pause_turn resumed)', bodies.length === 3);
check('system: persona + KB cached', bodies[0].system[0].cache_control?.type === 'ephemeral' && /I&C\) lead engineer/.test(bodies[0].system[0].text));
check('project context block sent', /Client \/ standard basis/.test(bodies[0].system[1]?.text || ''));
check('web search tool declared', bodies[0].tools?.[0]?.type === 'web_search_20260209');
check('resume sends partial assistant (thinking + server tool + result)',
  JSON.stringify(bodies[1].messages.at(-1).content.map((b) => b.type)) === '["thinking","server_tool_use","web_search_tool_result"]');
check('server_tool_use input parsed', bodies[1].messages.at(-1).content[1].input?.query === 'NAMUR NE 43 failure current');
const hist = bodies[2].messages;
check('turn 2 history = user, assistant, user', hist.map((m) => m.role).join(',') === 'user,assistant,user');
check('assistant turn kept thinking signature + citations', hist[1].content[0].signature === 'sig-1' && hist[1].content.at(-1).citations?.length === 1);
check('table rendered', (await page.$$('.msg.assistant table')).length === 1);
check('web sources listed', (await page.textContent('.sources'))?.includes('NE 43 explained'));
check('searched query shown', (await page.textContent('.searched'))?.includes('NAMUR NE 43'));
check('no page errors', errors.length === 0);
if (process.env.SHOT) await page.screenshot({ path: process.env.SHOT });
await browser.close();
if (errors.length) console.log(errors);
process.exit(ok.every(Boolean) ? 0 : 1);
