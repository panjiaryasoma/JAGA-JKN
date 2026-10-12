import { ApiError } from './api.mjs';
import { observation } from './domain.mjs';

// Explicit read-only adapter. A failed live request never selects this adapter.
export class DemoClient {
  constructor(sample) { this.sample = sample; this.mode = 'preview'; }
  logout() {}
  async login() { throw new ApiError('PREVIEW_READ_ONLY'); }
  async send() { throw new ApiError('PREVIEW_READ_ONLY'); }
  async get(path) {
    const [route, raw = ''] = path.split('?');
    const params = new URLSearchParams(raw);
    const {companies, evidence, info, meta} = this.sample;
    const response = data => ({data, meta});
    const paged = (rows, defaultSize) => {
      const page = Number(params.get('page') || 1), page_size = Number(params.get('page_size') || defaultSize);
      if (!Number.isInteger(page) || !Number.isInteger(page_size) || page < 1 || page_size < 1 || page_size > 100) throw new ApiError('VALIDATION_ERROR',422);
      return {...response(rows.slice((page-1)*page_size,page*page_size)), pagination:{page,page_size,total:rows.length,total_pages:Math.ceil(rows.length/page_size)}};
    };
    if (route === '/dataset') return response(info);
    if (route === '/capabilities') return {data:{scope:'SYNTHETIC_PROTOTYPE',snapshot:'AVAILABLE',case_store:'UNAVAILABLE',authentication:'NOT_CONFIGURED',ml:'NOT_CONFIGURED',experimental_ml:'DISABLED',policy:'UNRESOLVED'}};
    if (route === '/ml/status') return {data:{status:'NOT_CONFIGURED', experimental_status:'DISABLED',prediction_available:false}};
    if (route === '/badan-usaha') {
      const term = (params.get('q') ?? '').trim().toLocaleLowerCase('id');
      return paged(companies.filter(c => (!term || `${c.id_badan_usaha} ${c.nama_badan_usaha ?? ''}`.toLocaleLowerCase('id').includes(term)) && ['provinsi','skala_usaha','kode_kbli'].every(k => !params.get(k) || c[k] === params.get(k))), 20);
    }
    if (route === '/dashboard') {
      const rows = evidence.filter(e => e.periode_bulan === params.get('periode_bulan'));
      if (!rows.length) throw new ApiError('NOT_FOUND',404);
      const data = {periode_bulan:params.get('periode_bulan'),company_count:rows.length};
      for (const name of ['registration','wage','contribution']) {
        const group = {discrepancy:{true:0,false:0,unknown:0},quality:{HIGH:0,MEDIUM:0,LOW:0},abstain_count:0};
        for (const row of rows) {
          const value = observation(row,name);
          group.discrepancy[value === true ? 'true' : value === false ? 'false' : 'unknown']++;
          group.quality[row[name].evidence_quality]++;
          group.abstain_count += Number(row[name].rule_result === 'ABSTAIN');
        }
        data[name] = group;
      }
      return response(data);
    }
    const match = route.match(/^\/badan-usaha\/(BU-\d{4})(?:\/evidence(?:\/(\d{4}-\d{2}))?)?$/);
    if (match) {
      const company = companies.find(c => c.id_badan_usaha === match[1]);
      if (!company) throw new ApiError('NOT_FOUND',404);
      if (!route.includes('/evidence')) return response(company);
      const rows = evidence.filter(e => e.id_badan_usaha === company.id_badan_usaha);
      if (match[2]) {
        const record = rows.find(e => e.periode_bulan === match[2]);
        if (!record) throw new ApiError('NOT_FOUND',404);
        return response(record);
      }
      return paged(rows.filter(e => (!params.get('period_from') || e.periode_bulan >= params.get('period_from')) && (!params.get('period_to') || e.periode_bulan <= params.get('period_to'))),24);
    }
    throw new ApiError('PREVIEW_READ_ONLY',403);
  }
}
