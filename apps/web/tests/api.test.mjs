import test from 'node:test';
import assert from 'node:assert/strict';
import { ApiClient, ApiError } from '../static/api.mjs';
import { MutationDraft } from '../static/domain.mjs';

const json = (body, status = 200, headers = {}) => new Response(JSON.stringify(body), {status, headers: {'Content-Type':'application/json', ...headers}});
test('login validates with /me before retaining a token; logout removes it', async () => {
  const seen = [];
  const api = new ApiClient(async (url, options) => {
    seen.push([url, options]);
    return json({data: {actor_id: 'petugas', role:'REVIEWER'}});
  });
  await api.login('secret-token');
  await api.get('/cases');
  assert.equal(seen[0][0], '/api/v1/me');
  assert.equal(seen[1][1].headers.Authorization, 'Bearer secret-token');
  api.logout();
  await api.get('/dataset');
  assert.equal(seen[2][1].headers.Authorization, undefined);
});
test('failed authentication does not set the submitted token', async () => {
  let fail = true, headers;
  const api = new ApiClient(async (_, options) => {
    headers = options.headers;
    return fail ? json({error:{code:'UNAUTHORIZED',request_id:'req-1'}},401) : json({data:{}});
  });
  await assert.rejects(api.login('bad'), e => e.code === 'UNAUTHORIZED');
  fail = false;
  await api.get('/dataset');
  assert.equal(headers.Authorization, undefined);
});
test('412 retains conflict semantics and sanitized request ID', async () => {
  const api = new ApiClient(async () => json({error:{code:'VERSION_CONFLICT',request_id:'req-2'}},412));
  await assert.rejects(api.get('/cases/x'), e => e instanceof ApiError && e.status === 412 && e.requestId === 'req-2' && !e.uncertain);
});
test('a lost response remains uncertain and retry sends identical command', async () => {
  const seen = [];
  const api = new ApiClient(async (_, options) => {
    seen.push(options);
    if (seen.length === 1) throw new TypeError('network lost');
    return json({data:{case_id:'123'}},201,{'etag':'"v1"'});
  });
  const draft = new MutationDraft('/cases', {reason:'catatan'}, null, 'idempotent-test');
  await assert.rejects(api.send(draft), e => e.uncertain === true);
  const result = await api.send(draft);
  assert.equal(result.etag, '"v1"');
  assert.equal(seen[0].body, seen[1].body);
  assert.deepEqual(seen[0].headers, seen[1].headers);
  assert.equal(seen[0].headers['If-Match'], undefined);
});
test('invalid JSON or a server failure never masquerades as empty data', async () => {
  const api = new ApiClient(async () => new Response('<html>unavailable</html>',{status:503}));
  await assert.rejects(api.get('/dataset'), e => e.status === 503);
  await assert.rejects(api.send(new MutationDraft('/cases',{},null,'command-test')), e => e.uncertain);
});
test('client does not send credentials outside the fixed API origin', async () => {
  const api = new ApiClient(async () => { throw Error('must not fetch'); });
  await assert.rejects(api.get('https://example.com'), /path/i);
});
test('a cancelled or superseded login cannot replace the current session', async () => {
  let release;
  const seen=[];
  const api=new ApiClient(async (url,options)=>{
    seen.push(options.headers.Authorization);
    if (options.headers.Authorization==='Bearer old') return new Promise(resolve=>{ release=()=>resolve(json({data:{actor_id:'old',role:'REVIEWER'}})); });
    return json({data:{actor_id:'new',role:'SUPERVISOR'}});
  });
  const old=api.login('old');
  api.logout();
  await api.login('new');
  release();
  await assert.rejects(old,e=>e.name==='AbortError');
  await api.get('/cases');
  assert.equal(seen.at(-1),'Bearer new');
});
