import { DOMAIN, ACTION, STATUS, INTERVENTION, escapeHTML, number, monthLabel, periodsBetween, validMonth, parseRoute, href, query, allowedActions, assertSnapshot, MutationDraft } from './domain.mjs';
import { ApiClient, ApiError } from './api.mjs';
import { DemoClient } from './demo.mjs';
import { SAMPLE } from './sample.mjs';
import { icon, homePage, guidePage, shell, loadingPage, errorPage, overviewPage, companiesPage, evidencePage, loginGate, casesPage, casePage, dataPage, walkContent, mlView } from './views.mjs';

const client = window.JAGA_PREVIEW === true ? new DemoClient(SAMPLE) : new ApiClient();
const root = document.getElementById('app');
const modal = document.getElementById('modal');
const announce = document.getElementById('announcer');
const state = {mode:client.mode, actor:null, month:'2025-12', periods:periodsBetween(SAMPLE.info.period_from,SAMPLE.info.period_to), capabilities:null, company:null, record:null, item:null, dataset:null};
let routeGeneration=0, routeAbort=null, currentHash=location.hash||'#/', dialogContext=null, dialogReturnFocus=null, toastTimer;

function notify(message) {
  const host=document.getElementById('toast');
  host.textContent=message; host.classList.add('visible');
  clearTimeout(toastTimer); toastTimer=setTimeout(()=>host.classList.remove('visible'),6500);
}
function navigate(path, params = {}) {
  const target=href(path,params);
  if (location.hash===target) renderRoute(); else location.hash=target;
}
function activeRoute() { return parseRoute(location.hash); }
function finishRender(html, title, focusTarget) {
  root.innerHTML=html;
  document.title=`${title} · JAGA-JKN`;
  announce.textContent=title;
  const focus=focusTarget && document.getElementById(focusTarget);
  if (focus) focus.focus({preventScroll:true});
  else {
    const heading=root.querySelector('h1');
    if (heading) { heading.tabIndex=-1; heading.focus({preventScroll:true}); }
  }
  const tablist=root.querySelector('.walk-tabs');
  if (tablist) tablist.setAttribute('aria-orientation',matchMedia('(max-width:720px)').matches?'horizontal':'vertical');
}
async function renderRoute({focusTarget=null} = {}) {
  const generation=++routeGeneration;
  routeAbort?.abort(); routeAbort=new AbortController();
  const signal=routeAbort.signal, {path,params}=activeRoute();
  currentHash=location.hash||'#/';
  state.company=null; state.record=null; state.item=null;
  if (path==='/') {
    finishRender(homePage(SAMPLE),'Dari bukti menuju telaah yang utuh',focusTarget);
    const section=params.get('section');
    if (['how','principles'].includes(section)) document.getElementById(section)?.scrollIntoView();
    else window.scrollTo(0,0);
    return;
  }
  if (path==='/guide') { finishRender(guidePage(SAMPLE),'Panduan penggunaan',focusTarget); window.scrollTo(0,0); return; }
  let active=path.startsWith('/companies')?'companies':path.startsWith('/cases')?'cases':path==='/data'?'data':'workspace';
  const titles={workspace:'Ringkasan',companies:'Badan usaha',cases:'Kasus review',data:'Tentang data'};
  root.innerHTML=shell(loadingPage(),state,active,titles[active]);
  try {
    let html;
    const selectedMonth=params.get('month');
    if (selectedMonth && !validMonth(selectedMonth)) throw new ApiError('VALIDATION_ERROR',422);
    if (selectedMonth) state.month=selectedMonth;
    if (active==='cases') {
      // Persisted cases remain readable when the active dataset cannot load.
      if (!state.actor) html=loginGate(state);
      else if (path==='/cases') {
        const filters=Object.fromEntries(['status','id_badan_usaha','periode_bulan','page'].map(k=>[k,params.get(k)]));
        const response=await client.get('/cases'+query({...filters,page_size:12}),signal);
        html=casesPage(response,state,params);
      } else {
        const caseId=path.slice('/cases/'.length);
        if (!/^[a-f0-9-]{36}$/.test(caseId)) throw new ApiError('NOT_FOUND',404);
        const [detail,events]=await Promise.all([client.get(`/cases/${caseId}`,signal),client.get(`/cases/${caseId}/events`+query({page:params.get('page')??1,page_size:20}),signal)]);
        if (generation!==routeGeneration) return;
        state.item=detail.data; state.caseETag=detail.etag;
        html=casePage(detail.data,events,state,params);
      }
    } else {
      const [dataset,capabilities]=await Promise.all([client.get('/dataset',signal),client.get('/capabilities',signal)]);
      if (generation!==routeGeneration) return;
      state.dataset=dataset; state.capabilities=capabilities.data;
      state.periods=periodsBetween(dataset.data.period_from,dataset.data.period_to);
      if (!state.periods.includes(state.month)) {
        if (selectedMonth) throw new ApiError('NOT_FOUND',404);
        state.month=state.periods[0];
      }
      if (path==='/workspace') {
        const [dashboard,companies]=await Promise.all([client.get('/dashboard'+query({periode_bulan:state.month}),signal),client.get('/badan-usaha?page_size=5',signal)]);
        assertSnapshot(dataset,dashboard,companies);
        html=overviewPage(dashboard,companies,state);
      } else if (path==='/companies') {
        const filters=Object.fromEntries(['q','provinsi','skala_usaha','page'].map(k=>[k,params.get(k)]));
        const response=await client.get('/badan-usaha'+query({...filters,page_size:12}),signal);
        assertSnapshot(dataset,response);
        html=companiesPage(response,state,params);
      } else if (/^\/companies\/BU-\d{4}$/.test(path)) {
        const companyId=path.slice('/companies/'.length), domain=params.get('domain')??'registration';
        if (!Object.hasOwn(DOMAIN,domain)) throw new ApiError('NOT_FOUND',404);
        const [company,record,history]=await Promise.all([client.get(`/badan-usaha/${companyId}`,signal),client.get(`/badan-usaha/${companyId}/evidence/${state.month}`,signal),client.get(`/badan-usaha/${companyId}/evidence?page_size=100`,signal)]);
        assertSnapshot(dataset,company,record,history);
        if (history.pagination.total>history.data.length) throw Error('Riwayat lebih panjang dari cakupan tampilan. Hubungi pengelola.');
        if (generation!==routeGeneration) return;
        state.company=company.data; state.record=record.data;
        html=evidencePage(company.data,record.data,history.data,dataset.meta,state,domain);
      } else if (path==='/data') html=dataPage(dataset,capabilities.data,state);
      else html='<section class="panel"><div class="empty"><h1>Halaman tidak ditemukan.</h1><p>Pilih halaman dari navigasi untuk melanjutkan.</p><a class="btn" href="#/workspace">Kembali ke ringkasan</a></div></section>';
    }
    if (generation!==routeGeneration) return;
    finishRender(shell(html,state,active,titles[active]),titles[active],focusTarget);
    if (!focusTarget) window.scrollTo(0,0);
  } catch (error) {
    if (generation!==routeGeneration || error.name==='AbortError') return;
    if (error.status===401) { client.logout(); state.actor=null; }
    finishRender(shell(error.status===401?loginGate(state):errorPage(error),state,active,titles[active]),'Layanan belum tersedia',focusTarget);
  }
}

function showDialog(title, content, context = {}) {
  if (dialogContext?.locked) return;
  dialogReturnFocus=document.activeElement;
  dialogContext=context;
  modal.innerHTML=`<header class="dialog-head"><div><div class="eyebrow">JAGA-JKN · Ruang telaah</div><h2 id="dialog-title">${escapeHTML(title)}</h2></div><button type="button" class="icon-btn" data-action="close-dialog" aria-label="Tutup dialog">${icon('close')}</button></header><div class="dialog-body">${content}</div>`;
  if (!modal.open) modal.showModal();
  (modal.querySelector('input,textarea,select')??modal.querySelector('button'))?.focus();
}
function closeDialog() {
  if (dialogContext?.locked) { notify('Status penyimpanan belum pasti. Coba kembali dengan permintaan yang sama.'); return; }
  if (dialogContext?.type==='login' && dialogContext.busy) client.logout();
  modal.close(); modal.replaceChildren(); dialogContext=null;
  if (dialogReturnFocus?.isConnected) dialogReturnFocus.focus();
}
function showLogin(afterLogin = null) {
  if (state.mode==='preview') {
    showDialog('Anda sedang membuka preview.',`<p>Anda dapat menjelajahi cuplikan bukti tanpa masuk. Untuk mencatat kasus, jalankan aplikasi yang terhubung ke backend dan gunakan kunci akses petugas dari pengelola.</p><div class="dialog-actions"><button class="btn secondary" data-action="close-dialog" type="button">Lanjutkan penjelajahan</button></div>`);
    return;
  }
  showDialog('Masuk sebagai petugas.',`<p>Gunakan kunci akses prototipe dari pengelola. Peran reviewer atau supervisor mengikuti akses yang diberikan.</p><form id="login-form"><div class="field"><label for="access-key">Kunci akses petugas</label><input id="access-key" name="token" type="password" required minlength="32" maxlength="256" autocomplete="off" spellcheck="false"><p class="field-help">Akses hanya berlaku di tab ini. Muat ulang halaman untuk mengakhiri sesi.</p></div><div class="dialog-error" id="form-error" role="alert"></div><div class="dialog-actions"><button class="btn secondary" data-action="close-dialog" type="button">Batal</button><button class="btn" type="submit">Masuk ${icon('arrow')}</button></div></form>`,{type:'login',afterLogin});
}
function showAccount() {
  showDialog('Akses petugas aktif.',`<dl class="key-value" style="margin:10px 0 25px"><div><dt>Identitas pemeriksa</dt><dd>${escapeHTML(state.actor.actor_id)}</dd></div><div><dt>Peran</dt><dd>${state.actor.role==='SUPERVISOR'?'Supervisor':'Reviewer'}</dd></div></dl><p>Catatan dan tindakan disimpan bersama identitas pemeriksa ini.</p><div class="dialog-actions"><button class="btn secondary" data-action="close-dialog" type="button">Kembali</button><button class="btn" data-action="logout" type="button">Keluar dari sesi</button></div>`);
}
function showMutation(type, value = '') {
  if (!state.actor) { showLogin(()=>showMutation(type,value)); return; }
  if (state.mode==='preview') { showLogin(); return; }
  const item=state.item, company=state.company, record=state.record;
  if (type==='create' && (!company || !record)) return;
  if (type!=='create' && !item) return;
  const id=type==='create'?company.id_badan_usaha:item.id_badan_usaha, period=type==='create'?record.periode_bulan:item.periode_bulan;
  const ctx={type,value,item,companyId:id,period,version:item?.version,etag:state.caseETag,command:null,locked:false,conflict:false};
  let title, fields, path, submit='Simpan catatan';
  const textarea=(label,name,placeholder)=>`<div class="field"><label for="mutation-text">${label}</label><textarea id="mutation-text" name="${name}" required maxlength="2000" placeholder="${placeholder}"></textarea><p class="field-help">Jelaskan konteks dan alasan pemeriksaan. Maksimal 2.000 karakter.</p></div>`;
  if (type==='create') {
    title='Buka kasus review.'; path='/cases'; submit='Buka kasus';
    fields=textarea('Alasan membuka kasus','reason','Apa yang perlu ditelusuri dari bukti periode ini?')+`<details><summary>Hubungkan dengan kasus terdahulu (opsional)</summary><div class="field"><label for="recurrence">ID kasus terdahulu</label><input id="recurrence" name="recurrence_of" pattern="[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}" placeholder="ID lengkap kasus sebelumnya"><p class="field-help">Harus sudah selesai, badan usaha yang sama, dan periode lebih awal. Hubungan dicatat manual.</p></div></details>`;
  } else if (type==='transition') {
    if (!allowedActions(item.status,state.actor.role).includes(value)) return;
    title=ACTION[value]+'.'; path=`/cases/${item.case_id}/transitions`; submit=ACTION[value];
    fields=textarea('Alasan perubahan status','reason','Tuliskan dasar dan konteks perubahan status review.');
  } else if (type==='note') {
    title='Tambah catatan pemeriksaan.'; path=`/cases/${item.case_id}/notes`;
    fields=textarea('Catatan pemeriksaan','text','Apa yang telah diperiksa? Bukti apa yang masih diperlukan?');
  } else if (type==='intervention') {
    title='Catat rencana tindak lanjut.'; path=`/cases/${item.case_id}/interventions`; submit='Simpan rencana';
    fields=`<div class="field"><label for="intervention-kind">Jenis rencana</label><select id="intervention-kind" name="kind">${Object.entries(INTERVENTION).map(([key,label])=>`<option value="${key}">${label}</option>`).join('')}</select></div>`+textarea('Tujuan dan rincian rencana','note','Apa yang perlu dilakukan untuk melengkapi telaah?')+`<div class="field"><label for="due-time">Target waktu (opsional, waktu perangkat Anda)</label><input type="datetime-local" id="due-time" name="due_at"><p class="field-help">Rencana ini dicatat di aplikasi. Tidak ada pesan yang dikirim otomatis.</p></div>`;
  } else if (type==='outcome') {
    if (!item.interventions.some(i=>i.intervention_id===value&&i.status==='PLANNED')) return;
    title='Catat hasil tindak lanjut.'; path=`/cases/${item.case_id}/interventions/${value}/outcomes`;
    fields=`<div class="field"><label for="outcome-kind">Hasil rencana</label><select id="outcome-kind" name="outcome"><option value="COMPLETED">Selesai dilakukan</option><option value="CANCELLED">Dibatalkan</option></select></div>`+textarea('Catatan hasil atau alasan pembatalan','note','Tuliskan hasil dan konteks pelaksanaan rencana.');
  }
  ctx.path=path; ctx.submit=submit;
  showDialog(title,`<div class="dialog-context"><b>${escapeHTML(id)}</b> · ${escapeHTML(monthLabel(period))}<br>${type==='create'?'Kasus menyimpan salinan bukti periode ini.':`Status ${escapeHTML(STATUS[item.status])} · Versi ${item.version}`}</div><form id="mutation-form">${fields}<div class="dialog-error" id="form-error" role="alert"></div><div id="conflict-resolution"></div><div class="dialog-actions"><button class="btn secondary" data-action="close-dialog" type="button">Batal</button><button class="btn" type="submit">${escapeHTML(submit)}</button></div></form>`,ctx);
}
function mutationPayload(ctx, form) {
  const data=Object.fromEntries(new FormData(form));
  for (const key of ['reason','text','note']) if (Object.hasOwn(data,key)) {
    data[key]=data[key].trim();
    if (!data[key] || data[key].includes('\0')) throw new ApiError('VALIDATION_ERROR',422);
  }
  if (ctx.type==='create') return {id_badan_usaha:ctx.companyId,periode_bulan:ctx.period,reason:data.reason,...(data.recurrence_of?{recurrence_of:data.recurrence_of.trim()}:{})};
  if (ctx.type==='transition') return {action:ctx.value,reason:data.reason};
  if (ctx.type==='note') return {text:data.text};
  if (ctx.type==='intervention') return {kind:data.kind,note:data.note,...(data.due_at?{due_at:new Date(data.due_at).toISOString()}:{})};
  return {outcome:data.outcome,note:data.note};
}
function lockMutationForm(locked) {
  for (const element of modal.querySelectorAll('input,textarea,select,[data-action="close-dialog"]')) element.disabled=locked;
}
async function submitMutation(form) {
  const ctx=dialogContext;
  if (!ctx || ctx.busy || ctx.conflict) return;
  const errorBox=document.getElementById('form-error'), button=form.querySelector('[type="submit"]');
  errorBox.textContent='';
  try {
    if (!ctx.command) ctx.command=new MutationDraft(ctx.path,mutationPayload(ctx,form),ctx.type==='create'?null:ctx.etag);
    ctx.busy=true; ctx.locked=true; lockMutationForm(true); button.disabled=true; button.textContent='Menyimpan…';
    const result=await client.send(ctx.command);
    ctx.locked=false; ctx.busy=false;
    closeDialog();
    notify('Perubahan tersimpan. Memuat keadaan kasus terbaru.');
    navigate('/cases/'+result.data.case_id);
  } catch (error) {
    ctx.busy=false;
    if (error.uncertain) {
      ctx.locked=true;
      errorBox.textContent='Status penyimpanan belum dapat dipastikan. Coba lagi untuk memeriksa permintaan yang sama; jangan membuat tindakan baru.';
      button.disabled=false; button.textContent='Periksa & coba lagi';
    } else {
      ctx.locked=false; ctx.command=null; lockMutationForm(false);
      errorBox.textContent=error.message;
      if (error.requestId) errorBox.textContent+=` ID permintaan: ${error.requestId}`;
      button.textContent=ctx.submit; button.disabled=false;
      if (error.status===412) {
        ctx.conflict=true; button.disabled=true;
        document.getElementById('conflict-resolution').innerHTML='<button type="button" class="btn secondary" data-action="refresh-case">Muat versi terbaru</button>';
      }
    }
    errorBox.tabIndex=-1; errorBox.focus();
  }
}
async function refreshCaseVersion() {
  const ctx=dialogContext;
  if (!ctx?.conflict || ctx.busy) return;
  const host=document.getElementById('conflict-resolution');
  ctx.busy=true; host.textContent='Memuat perubahan terbaru…';
  try {
    const result=await client.get(`/cases/${ctx.item.case_id}`);
    const updates=await client.get(`/cases/${ctx.item.case_id}/events`+query({page:Math.ceil(result.data.version/20),page_size:20}));
    ctx.item=result.data; ctx.etag=result.etag; ctx.version=result.data.version;
    const terminal=['RESOLVED','DISMISSED'].includes(ctx.item.status);
    const allowed=ctx.type==='transition'?allowedActions(ctx.item.status,state.actor.role).includes(ctx.value):ctx.type==='intervention'?['IN_REVIEW','WAITING_EVIDENCE'].includes(ctx.item.status):ctx.type==='outcome'?!terminal&&ctx.item.interventions.some(i=>i.intervention_id===ctx.value&&i.status==='PLANNED'):!terminal;
    host.innerHTML=`<div class="notice" style="margin-top:14px"><b>Versi terbaru: ${ctx.version} · ${escapeHTML(STATUS[ctx.item.status])}</b><br>Alasan status: ${escapeHTML(ctx.item.status_reason)}<br>Rencana belum selesai: ${ctx.item.interventions.filter(i=>i.status==='PLANNED').length}</div><details open><summary>Catatan pada halaman riwayat terbaru</summary><div>${updates.data.map(ev=>`<p class="small break">v${ev.version} · ${escapeHTML(ev.actor_id)}: ${escapeHTML(ev.payload.text??ev.payload.reason??ev.payload.note??ev.action)}</p>`).join('')}</div></details>${allowed?'<label class="checkbox"><input type="checkbox" id="conflict-reviewed" required>Saya sudah membaca perubahan ini dan ingin mengajukan kembali tindakan saya.</label>':'<p class="dialog-error">Tindakan ini tidak tersedia pada status terbaru. Tutup dialog dan muat ulang kasus.</p>'}`;
    ctx.conflict=true;
    modal.querySelector('[type="submit"]').disabled=true;
  } catch (error) {
    host.innerHTML=`<p class="dialog-error">${escapeHTML(error.message)}</p><button type="button" class="btn secondary" data-action="refresh-case">Coba muat versi terbaru</button>`;
  } finally { ctx.busy=false; }
}
async function loadML() {
  if (!state.actor) { showLogin(loadML); return; }
  if (!state.company || !state.record) return;
  const generation=routeGeneration, id=state.company.id_badan_usaha, month=state.month;
  const host=document.getElementById('ml-result');
  if (!host) return;
  const button=root.querySelector('[data-action="ml"]'); button.disabled=true;
  host.innerHTML='<p style="margin-top:15px" role="status">Menghitung eksperimen…</p>';
  try {
    const result=await client.get(`/ml/experimental/badan-usaha/${id}/${month}`,routeAbort.signal);
    if (generation!==routeGeneration) return;
    assertSnapshot(state.dataset,result);
    host.innerHTML=mlView(result.data);
  } catch(error) {
    if (generation===routeGeneration && error.name!=='AbortError') host.innerHTML=`<p class="dialog-error">${escapeHTML(error.message)}</p>`;
  } finally { if (button.isConnected) button.disabled=false; }
}

document.addEventListener('click', async event => {
  const target=event.target.closest('button,a');
  if (!target) return;
  if (target.classList.contains('skip')) { event.preventDefault(); document.getElementById('main')?.focus(); return; }
  const walk=target.dataset.walk;
  if (walk!==undefined) {
    const step=Number(walk);
    for (const tab of root.querySelectorAll('[data-walk]')) { const on=tab===target; tab.setAttribute('aria-selected',String(on)); tab.tabIndex=on?0:-1; }
    const panel=document.getElementById('walk-panel'); panel.innerHTML=walkContent(step,SAMPLE); panel.setAttribute('aria-labelledby',target.id); return;
  }
  if (target.dataset.period) { const route=activeRoute(); navigate(route.path,{...Object.fromEntries(route.params),month:target.dataset.period}); return; }
  if (target.dataset.transition) { showMutation('transition',target.dataset.transition); return; }
  if (target.dataset.outcome) { showMutation('outcome',target.dataset.outcome); return; }
  const action=target.dataset.action;
  if (!action) return;
  if (action==='menu') { const shellElement=root.querySelector('.shell'), open=shellElement.classList.toggle('nav-open'); target.setAttribute('aria-expanded',String(open)); target.setAttribute('aria-label',open?'Tutup navigasi':'Buka navigasi'); }
  if (action==='reload') renderRoute();
  if (action==='login') showLogin();
  if (action==='account') showAccount();
  if (action==='logout') { client.logout(); state.actor=null; closeDialog(); notify('Anda sudah keluar dari sesi.'); renderRoute(); }
  if (action==='close-dialog') closeDialog();
  if (action==='create-case') showMutation('create');
  if (action==='note') showMutation('note');
  if (action==='intervention') showMutation('intervention');
  if (action==='refresh-case') await refreshCaseVersion();
  if (action==='ml') await loadML();
});
document.addEventListener('change', event => {
  if (event.target.id==='active-month') {
    const route=activeRoute(); navigate(route.path,{...Object.fromEntries(route.params),month:event.target.value});
  }
  if (event.target.id==='conflict-reviewed' && dialogContext) {
    dialogContext.conflict=!event.target.checked;
    modal.querySelector('[type="submit"]').disabled=!event.target.checked;
  }
});
document.addEventListener('submit', async event => {
  const form=event.target;
  if (!['quick-search','company-filters','case-filters','login-form','mutation-form'].includes(form.id)) return;
  event.preventDefault();
  if (form.id==='mutation-form') { await submitMutation(form); return; }
  if (form.id==='login-form') {
    const context=dialogContext;
    if (context.busy) return;
    const button=form.querySelector('[type="submit"]'); button.disabled=true; context.busy=true;
    document.getElementById('form-error').textContent='';
    try {
      const actor=await client.login(new FormData(form).get('token').trim());
      if (dialogContext!==context) return;
      state.actor=actor; context.busy=false; form.reset(); closeDialog();
      await renderRoute(); notify(`Masuk sebagai ${actor.role==='SUPERVISOR'?'supervisor':'reviewer'}.`);
      context.afterLogin?.();
    } catch(error) {
      if (dialogContext===context) document.getElementById('form-error').textContent=error.message;
    } finally { context.busy=false; if (button.isConnected) button.disabled=false; }
    return;
  }
  const params=Object.fromEntries([...new FormData(form)].map(([key,value])=>[key,value.trim()]));
  navigate(form.id==='case-filters'?'/cases':'/companies',{...(form.id==='case-filters'?{}:{month:state.month}),...params});
});
document.addEventListener('keydown', event => {
  if (event.key==='Escape' && !modal.open) {
    root.querySelector('.shell')?.classList.remove('nav-open');
    root.querySelector('[data-action="menu"]')?.setAttribute('aria-expanded','false');
  }
  if (event.target.matches('[data-walk]') && ['ArrowDown','ArrowUp','ArrowRight','ArrowLeft','Home','End'].includes(event.key)) {
    event.preventDefault();
    const tabs=[...root.querySelectorAll('[data-walk]')], i=tabs.indexOf(event.target);
    const next=event.key==='Home'?0:event.key==='End'?tabs.length-1:(i+(['ArrowDown','ArrowRight'].includes(event.key)?1:-1)+tabs.length)%tabs.length;
    tabs[next].click(); tabs[next].focus();
  }
});
modal.addEventListener('cancel', event => { event.preventDefault(); closeDialog(); });
window.addEventListener('beforeunload', event => { if (dialogContext?.locked) { event.preventDefault(); event.returnValue=''; } });
window.addEventListener('hashchange', () => {
  if (dialogContext?.locked) { history.replaceState(null,'',currentHash); notify('Selesaikan pemeriksaan status penyimpanan sebelum berpindah halaman.'); return; }
  if (modal.open) closeDialog();
  renderRoute({focusTarget:document.activeElement?.id==='active-month'?'active-month':null});
});
renderRoute();
