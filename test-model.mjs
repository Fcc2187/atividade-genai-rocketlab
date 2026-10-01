// Prova de instalação; não acessa o banco nem utiliza serviços externos.
import assert from 'node:assert/strict';
import { writeFile } from 'node:fs/promises';

const base = 'http://127.0.0.1:8081/v1';
const measurements = [];
async function request(path, body) {
  const start = performance.now();
  const response = await fetch(`${base}${path}`, {
    method: body ? 'POST' : 'GET',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
    signal: AbortSignal.timeout(180_000),
  });
  const data = await response.json();
  assert.ok(response.ok, JSON.stringify(data));
  measurements.push({ path, seconds: (performance.now() - start) / 1000, usage: data.usage, timings: data.timings });
  return data;
}
const catalog = await request('/models');
assert.ok(catalog.data.some(model => model.id === 'qwen3.5-9b'));
const settings = { model: 'qwen3.5-9b', temperature: 0, max_tokens: 1024, chat_template_kwargs: { enable_thinking: false } };
const greeting = await request('/chat/completions', { ...settings, messages: [{ role: 'user', content: 'Responda em português com uma saudação curta.' }] });
assert.ok(greeting.choices[0].message.content?.trim());
assert.equal(greeting.choices[0].finish_reason, 'stop');
const tools = [{ type: 'function', function: { name: 'somar', description: 'Soma dois inteiros.', parameters: { type: 'object', properties: { a: { type: 'integer' }, b: { type: 'integer' } }, required: ['a', 'b'], additionalProperties: false } } }];
const messages = [{ role: 'user', content: 'Use a ferramenta somar para somar 7 e 5. Depois responda apenas com o resultado numérico.' }];
const invocation = await request('/chat/completions', { ...settings, messages, tools, tool_choice: 'auto' });
const call = invocation.choices[0].message.tool_calls?.[0];
assert.equal(call?.function.name, 'somar');
assert.deepEqual(JSON.parse(call.function.arguments), { a: 7, b: 5 });
const answer = await request('/chat/completions', { ...settings, tools, tool_choice: 'none', messages: [...messages, invocation.choices[0].message, { role: 'tool', tool_call_id: call.id, content: '12' }] });
assert.equal(answer.choices[0].message.content?.trim(), '12');
assert.equal(answer.choices[0].finish_reason, 'stop');
const report = { passed: true, date: new Date().toISOString(), greeting: greeting.choices[0].message.content, tool: call, answer: answer.choices[0].message.content, measurements };
await writeFile(new URL('./runtime/smoke-result.json', import.meta.url), JSON.stringify(report, null, 2));
console.log(JSON.stringify(report, null, 2));
