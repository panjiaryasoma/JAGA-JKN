export const DOMAIN = {
  registration: { name: 'Kepesertaan', short: 'Pekerja', icon: 'people', description: 'Bandingkan referensi pekerja dengan kepesertaan yang tercatat.' },
  wage: { name: 'Sinyal upah', short: 'Upah', icon: 'receipt', description: 'Telusuri perbedaan sinyal upah referensi dan yang teramati.' },
  contribution: { name: 'Pembayaran', short: 'Pembayaran', icon: 'calendar', description: 'Baca status pembayaran beserta ketersediaan buktinya.' },
};
export const STATUS = { OPEN: 'Terbuka', IN_REVIEW: 'Dalam telaah', WAITING_EVIDENCE: 'Menunggu bukti', RESOLVED: 'Review selesai', DISMISSED: 'Ditutup tanpa lanjut' };
export const ACTION = { START_REVIEW: 'Mulai telaah', REQUEST_EVIDENCE: 'Tandai menunggu bukti', RESUME_REVIEW: 'Lanjutkan telaah', RESOLVE: 'Selesaikan review', DISMISS: 'Tutup tanpa tindak lanjut', REOPEN: 'Buka kembali' };
export const PAYMENT = { PAID_ON_TIME: 'Terbayar tepat waktu', PAYMENT_PENDING: 'Pembayaran tertunda', UNPAID: 'Belum terbayar', UNKNOWN: 'Belum diketahui' };
export const QUALITY = { HIGH: 'Tinggi', MEDIUM: 'Sedang', LOW: 'Rendah' };
export const INTERVENTION = { REQUEST_DOCUMENTS: 'Permintaan dokumen', CONTACT_REVIEW: 'Kontak untuk telaah', FOLLOW_UP: 'Tindak lanjut' };
export const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[char]));
export const number = value => value === null || value === undefined || !Number.isFinite(value) ? 'Belum tersedia' : new Intl.NumberFormat('id-ID', {maximumFractionDigits: 2}).format(value);
export const rupiah = value => value === null || value === undefined ? 'Belum tersedia' : `Rp${number(value)}`;
export const shortMoney = value => value === null || value === undefined ? '—' : new Intl.NumberFormat('id-ID', {notation:'compact', maximumFractionDigits:1}).format(value);
export const percent = (value, total) => total > 0 ? Math.max(0, Math.min(100, value / total * 100)) : 0;
export const monthLabel = (period, short = false) => validMonth(period) ? new Intl.DateTimeFormat('id-ID', {month:short ? 'short' : 'long', year:'numeric', timeZone:'UTC'}).format(new Date(`${period}-01T00:00:00Z`)) : 'Periode tidak valid';
export const timeLabel = value => value ? new Intl.DateTimeFormat('id-ID', {dateStyle:'medium', timeStyle:'short', timeZone:'Asia/Jakarta'}).format(new Date(value)) + ' WIB' : 'Belum tersedia';
export function validMonth(value) { return typeof value === 'string' && /^(?!0000)\d{4}-(0[1-9]|1[0-2])$/.test(value); }
export function periodsBetween(start, end) {
  if (!validMonth(start) || !validMonth(end)) throw Error('Invalid calendar month');
  const ordinal = value => Number(value.slice(0,4)) * 12 + Number(value.slice(5)) - 1;
  const a = ordinal(start), b = ordinal(end);
  if (b < a || b - a > 119) throw Error('Invalid period range');
  return Array.from({length:b-a+1}, (_, i) => `${Math.floor((a+i)/12).toString().padStart(4,'0')}-${((a+i)%12+1).toString().padStart(2,'0')}`);
}
export function discrepancy(value) {
  if (value === true) return { label:'Ada perbedaan', tone:'amber', key:'true' };
  if (value === false) return { label:'Tidak teramati', tone:'green', key:'false' };
  return { label:'Belum diketahui', tone:'gray', key:'unknown' };
}
export const observation = (record, domain) => domain === 'contribution' ? record.contribution.payment_gap_observed : record[domain].discrepancy_detected;
export function parseRoute(hash = '') {
  const input = hash.replace(/^#/, '') || '/';
  const pos = input.indexOf('?');
  return {path:(pos < 0 ? input : input.slice(0,pos)), params:new URLSearchParams(pos < 0 ? '' : input.slice(pos+1))};
}
export function href(path, params = {}) {
  const query = new URLSearchParams();
  for (const [key,value] of Object.entries(params)) if (value !== null && value !== undefined && value !== '') query.set(key, String(value));
  return `#${path}${query.size ? '?' + query : ''}`;
}
export const query = params => href('', params).slice(1);
export function allowedActions(status, role) {
  if (!['REVIEWER','SUPERVISOR'].includes(role)) return [];
  const choices = { OPEN:['START_REVIEW'], IN_REVIEW:['REQUEST_EVIDENCE', ...(role === 'SUPERVISOR' ? ['RESOLVE','DISMISS'] : [])], WAITING_EVIDENCE:['RESUME_REVIEW'], RESOLVED:role === 'SUPERVISOR' ? ['REOPEN'] : [], DISMISSED:role === 'SUPERVISOR' ? ['REOPEN'] : [] };
  return choices[status] ?? [];
}
export function linePath(values, width, height, maximum) {
  let start = true;
  return values.map((value, i) => {
    if (value === null || value === undefined || !Number.isFinite(value)) { start = true; return ''; }
    const x = values.length > 1 ? i / (values.length-1) * width : 0;
    const y = height - value / (maximum || 1) * height;
    const command = `${start ? 'M' : 'L'}${+x.toFixed(2)},${+y.toFixed(2)}`;
    start = false;
    return command;
  }).filter(Boolean).join(' ');
}
export function assertSnapshot(...responses) {
  const ids = responses.map(r => r.meta?.dataset_id);
  if (ids.some(id => !id) || new Set(ids).size !== 1) throw Error('Identitas snapshot berubah. Muat ulang halaman sebelum melanjutkan.');
}
export class MutationDraft {
  constructor(path, body, etag = null, key = crypto.randomUUID()) {
    this.path = path;
    this.body = JSON.stringify(body);
    this.headers = Object.freeze({'Content-Type':'application/json', 'Idempotency-Key':key, ...(etag ? {'If-Match':etag} : {})});
    Object.freeze(this);
  }
}
