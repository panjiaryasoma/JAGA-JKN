import test from 'node:test';
import assert from 'node:assert/strict';
import { DemoClient } from '../static/demo.mjs';
import { SAMPLE } from '../static/sample.mjs';
import { observation, query } from '../static/domain.mjs';

const demo=new DemoClient(SAMPLE);
test('preview counts refer to its explicit eight-company sample', async()=>{
  const dataset=await demo.get('/dataset');
  assert.equal(dataset.data.company_count,8);
  assert.equal(dataset.data.evidence_record_count,192);
  assert.equal(SAMPLE.source_company_count,500);
  assert.equal(SAMPLE.scope,'READ_ONLY_SAMPLE');
});
test('aggregate counts are derived from records, preserving false and unknown', async()=>{
  for (const month of ['2025-01','2025-12','2026-12']) {
    const result=await demo.get('/dashboard'+query({periode_bulan:month}));
    const rows=SAMPLE.evidence.filter(r=>r.periode_bulan===month);
    for (const name of ['registration','wage','contribution']) {
      const c=result.data[name].discrepancy;
      assert.equal(c.true+c.false+c.unknown,8);
      assert.equal(c.unknown,rows.filter(r=>observation(r,name)===null).length);
      assert.equal(c.false,rows.filter(r=>observation(r,name)===false).length);
    }
  }
});
test('search and combined exact filters cannot invent results',async()=>{
  const hit=await demo.get('/badan-usaha'+query({q:'BU-0001',provinsi:'Jawa Timur',skala_usaha:'Menengah'}));
  assert.equal(hit.pagination.total,1);
  assert.equal(hit.data[0].id_badan_usaha,'BU-0001');
  const miss=await demo.get('/badan-usaha'+query({q:'BU-0001',provinsi:'Riau'}));
  assert.equal(miss.pagination.total,0);
  assert.deepEqual(miss.data,[]);
});
test('history is ordered and inclusive, and absent evidence stays 404',async()=>{
  const result=await demo.get('/badan-usaha/BU-0001/evidence?period_from=2025-11&period_to=2026-01');
  assert.deepEqual(result.data.map(r=>r.periode_bulan),['2025-11','2025-12','2026-01']);
  await assert.rejects(demo.get('/badan-usaha/BU-0001/evidence/2024-01'),e=>e.status===404);
});
test('preview does not fake access, case writes, or model inference', async()=>{
  await assert.rejects(demo.login('token'),e=>e.code==='PREVIEW_READ_ONLY');
  await assert.rejects(demo.send({}),e=>e.code==='PREVIEW_READ_ONLY');
  await assert.rejects(demo.get('/ml/experimental/badan-usaha/BU-0001/2025-12'),e=>e.code==='PREVIEW_READ_ONLY');
});
