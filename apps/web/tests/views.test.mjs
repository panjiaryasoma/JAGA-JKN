import test from 'node:test';
import assert from 'node:assert/strict';
import { homePage, guidePage, evidencePage, companyTable, overviewPage, dataPage, casePage, casesPage, loginGate } from '../static/views.mjs';
import { SAMPLE } from '../static/sample.mjs';
import { DemoClient } from '../static/demo.mjs';
import { periodsBetween } from '../static/domain.mjs';
const state={mode:'preview',month:'2025-12',periods:periodsBetween('2025-01','2026-12'),capabilities:{experimental_ml:'DISABLED'},actor:null};
test('landing and guide point to real routes and a real sample record',()=>{
  const home=homePage(SAMPLE), guide=guidePage(SAMPLE);
  for (const route of ['#/workspace','#/guide','#/data']) assert.ok(home.includes(route));
  const match=guide.match(/#\/companies\/(BU-\d{4})\?month=(\d{4}-\d{2})/);
  assert.ok(match);
  assert.ok(SAMPLE.evidence.some(r=>r.id_badan_usaha===match[1]&&r.periode_bulan===match[2]));
});
test('company and evidence displays escape backend text and preserve null',()=>{
  const company={...SAMPLE.companies[0],nama_badan_usaha:'<img src=x onerror=alert(1)>'};
  const record=structuredClone(SAMPLE.evidence.find(r=>r.id_badan_usaha===company.id_badan_usaha&&r.periode_bulan===state.month));
  record.registration.reference_worker_count=null;
  record.registration.source_ids=['</dd><script>alert(1)</script>'];
  const history=SAMPLE.evidence.filter(r=>r.id_badan_usaha===company.id_badan_usaha);
  const output=evidencePage(company,record,history,SAMPLE.meta,state);
  assert.ok(!output.includes('<script>'));
  assert.ok(!output.includes('<img src=x'));
  assert.ok(output.includes('&lt;img'));
  assert.ok(output.includes('Belum tersedia'));
  assert.ok(output.includes('Belum dapat<br>diputuskan'));
  assert.ok(!output.includes('data-action="ml"'));
});
test('all directory entries have an explicit company route',()=>{
  const html=companyTable(SAMPLE.companies,state.month);
  for (const c of SAMPLE.companies) assert.ok(html.includes('#/companies/'+c.id_badan_usaha));
});
test('overview and provenance state the limited preview scope',async()=>{
  const demo=new DemoClient(SAMPLE);
  const [dashboard,companies,dataset,caps]=await Promise.all([demo.get('/dashboard?periode_bulan=2025-12'),demo.get('/badan-usaha'),demo.get('/dataset'),demo.get('/capabilities')]);
  assert.ok(overviewPage(dashboard,companies,state).includes('Dalam cuplikan ini'));
  assert.ok(dataPage(dataset,caps.data,state).includes('8 badan usaha pertama'));
  assert.ok(loginGate(state).includes('tidak menyimpan kasus'));
});
test('every persisted case and event is linked and safely rendered',()=>{
  const record=SAMPLE.evidence[0],id='00000000-0000-4000-8000-000000000001';
  const item={case_id:id,id_badan_usaha:record.id_badan_usaha,periode_bulan:record.periode_bulan,status:'IN_REVIEW',version:2,created_by:'reviewer',reason:'<script>x</script>',status_reason:'Mulai',updated_at:'2026-10-12T00:00:00Z',dataset:SAMPLE.meta,evidence_snapshot:record,interventions:[]};
  const pagination={page:1,page_size:20,total:1,total_pages:1};
  const events={data:[{actor_id:'reviewer',actor_role:'REVIEWER',created_at:'2026-10-12T00:00:00Z',version:2,action:'NOTE_ADDED',payload:{text:'<img onerror=alert(1)>'}}],pagination};
  const html=casePage(item,events,{...state,actor:{role:'REVIEWER'}},new URLSearchParams());
  assert.ok(!html.includes('<script>'));
  assert.ok(!html.includes('<img onerror='));
  assert.ok(html.includes('Catatan ditambahkan'));
  assert.ok(!html.includes('data-transition="RESOLVE"'));
  assert.ok(casesPage({data:[item],pagination},state,new URLSearchParams()).includes('#/cases/'+id));
});
