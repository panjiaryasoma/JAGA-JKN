import test from 'node:test';
import assert from 'node:assert/strict';
import { escapeHTML, number, discrepancy, periodsBetween, parseRoute, href, allowedActions, linePath, assertSnapshot, MutationDraft } from '../static/domain.mjs';

test('unknown, false and zero retain distinct meaning', () => {
  assert.equal(number(null), 'Belum tersedia');
  assert.equal(number(0), '0');
  assert.equal(discrepancy(null).label, 'Belum diketahui');
  assert.equal(discrepancy(false).label, 'Tidak teramati');
  assert.equal(discrepancy(true).label, 'Ada perbedaan');
});
test('untrusted text cannot create executable markup', () => {
  assert.equal(escapeHTML('<img onerror="x"> & \' </script>'), '&lt;img onerror=&quot;x&quot;&gt; &amp; &#39; &lt;/script&gt;');
});
test('calendar, routes and query values preserve explicit context', () => {
  assert.deepEqual(periodsBetween('2025-12', '2026-02'), ['2025-12', '2026-01', '2026-02']);
  assert.throws(() => periodsBetween('2025-13', '2026-02'));
  assert.throws(() => periodsBetween('2026-02', '2025-12'));
  const r = parseRoute(href('/companies', { q: 'a&b', month: '2025-12' }));
  assert.equal(r.path, '/companies');
  assert.equal(r.params.get('q'), 'a&b');
  assert.equal(r.params.get('month'), '2025-12');
});
test('reviewers cannot resolve cases; supervisors follow the state machine', () => {
  assert.deepEqual(allowedActions('IN_REVIEW', 'REVIEWER'), ['REQUEST_EVIDENCE']);
  assert.deepEqual(allowedActions('IN_REVIEW', 'SUPERVISOR'), ['REQUEST_EVIDENCE', 'RESOLVE', 'DISMISS']);
  assert.deepEqual(allowedActions('RESOLVED', 'REVIEWER'), []);
  assert.deepEqual(allowedActions('WAITING_EVIDENCE', 'SUPERVISOR'), ['RESUME_REVIEW']);
});
test('trend breaks its path around missing evidence', () => {
  assert.equal(linePath([2, null, 4], 100, 50, 4), 'M0,25 M100,0');
});
test('mixed snapshots cannot be presented as one context', () => {
  assert.doesNotThrow(() => assertSnapshot({ meta: { dataset_id: 'a' } }, { meta: { dataset_id: 'a' } }));
  assert.throws(() => assertSnapshot({ meta: { dataset_id: 'a' } }, { meta: { dataset_id: 'b' } }), /snapshot/i);
});
test('an uncertain mutation retries identical bytes and version', () => {
  const body = { reason: 'review' };
  const draft = new MutationDraft('/cases/123/transitions', body, '"v2"', 'same-command-123');
  body.reason = 'changed';
  assert.equal(draft.body, '{"reason":"review"}');
  assert.equal(draft.headers['If-Match'], '"v2"');
  assert.equal(draft.headers['Idempotency-Key'], 'same-command-123');
  assert.ok(Object.isFrozen(draft));
  assert.ok(Object.isFrozen(draft.headers));
});
