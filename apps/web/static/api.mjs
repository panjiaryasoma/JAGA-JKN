const MESSAGES = {
  NETWORK_ERROR:'Koneksi terputus. Periksa koneksi lalu coba kembali.',
  TIMEOUT:'Layanan belum merespons. Silakan coba kembali.',
  INVALID_RESPONSE:'Respons layanan tidak dapat dibaca. Silakan coba kembali.',
  NOT_FOUND:'Data yang diminta tidak ditemukan.',
  VALIDATION_ERROR:'Isian belum sesuai. Periksa kembali data yang dimasukkan.',
  UNAUTHORIZED:'Akses berakhir atau kunci akses tidak valid. Silakan masuk kembali.',
  FORBIDDEN:'Peran Anda tidak memiliki akses untuk tindakan ini.',
  AUTH_NOT_CONFIGURED:'Akses petugas belum diaktifkan oleh pengelola prototipe.',
  DATASET_UNAVAILABLE:'Dataset belum tersedia. Hubungi pengelola prototipe.',
  DATASET_INVALID:'Dataset tidak lolos pemeriksaan integritas. Data belum dapat ditampilkan.',
  PERSISTENCE_UNAVAILABLE:'Penyimpanan kasus sedang tidak tersedia.',
  CASE_ALREADY_OPEN:'Kasus aktif sudah ada untuk badan usaha dan periode ini. Buka daftar kasus untuk melanjutkan.',
  VERSION_CONFLICT:'Kasus telah berubah. Muat versi terbaru, baca perubahannya, lalu putuskan kembali.',
  INVALID_TRANSITION:'Tindakan ini tidak sesuai dengan status kasus saat ini.',
  OPEN_INTERVENTIONS:'Masih ada rencana tindak lanjut yang perlu diselesaikan atau dibatalkan.',
  INVALID_RECURRENCE:'Kasus terdahulu harus sudah selesai, berasal dari badan usaha yang sama, dan periodenya lebih awal.',
  IDEMPOTENCY_CONFLICT:'Permintaan ini tidak sesuai dengan percobaan sebelumnya. Muat ulang konteks kasus.',
  ML_EXPERIMENT_DISABLED:'Eksperimen model belum diaktifkan.',
  ML_ARTIFACT_UNAVAILABLE:'Model eksperimen belum tersedia.',
  ML_INFERENCE_UNAVAILABLE:'Model belum dapat menghasilkan keluaran yang valid.',
  PREVIEW_READ_ONLY:'Preview ini hanya untuk menjelajahi contoh. Pencatatan tersedia di aplikasi yang terhubung ke backend.',
};
export class ApiError extends Error {
  constructor(code, status = 0, requestId = '', uncertain = false) {
    super(MESSAGES[code] ?? 'Layanan mengalami kendala. Silakan coba kembali.');
    this.name = 'ApiError'; this.code = code; this.status = status; this.requestId = requestId; this.uncertain = uncertain;
  }
}
export class ApiClient {
  #token = '';
  #authGeneration = 0;
  constructor(fetcher = (...args) => fetch(...args)) { this.fetcher = fetcher; this.mode = 'live'; }
  logout() { this.#token = ''; this.#authGeneration++; }
  async login(token) {
    const generation = ++this.#authGeneration;
    const result = await this.request('/me', {token});
    if (generation !== this.#authGeneration) throw new DOMException('Authentication cancelled', 'AbortError');
    if (!['REVIEWER','SUPERVISOR'].includes(result.data?.role) || !result.data.actor_id) throw new ApiError('INVALID_RESPONSE');
    this.#token = token;
    return result.data;
  }
  get(path, signal) { return this.request(path, {signal}); }
  send(command) { return this.request(command.path, {method:'POST', body:command.body, headers:command.headers}); }
  async request(path, {method = 'GET', body, headers = {}, signal, token = this.#token} = {}) {
    if (!/^\/[a-z][a-z0-9/-]*(?:\?[^#]*)?$/i.test(path) || path.includes('..') || /[\\\r\n]/.test(path)) throw Error('Invalid API path');
    const timeout = new AbortController();
    const timer = setTimeout(() => timeout.abort(), 15000);
    const abort = () => timeout.abort();
    if (signal?.aborted) timeout.abort();
    signal?.addEventListener('abort', abort, {once:true});
    try {
      const response = await this.fetcher(`/api/v1${path}`, {
        method, body, headers:{Accept:'application/json', ...headers, ...(token ? {Authorization:`Bearer ${token}`} : {})},
        signal:timeout.signal, cache:'no-store', credentials:'omit', redirect:'error',
      });
      let data;
      try { data = await response.json(); } catch { throw new ApiError('INVALID_RESPONSE', response.status, '', method === 'POST'); }
      if (!response.ok) throw new ApiError(data.error?.code ?? 'INVALID_RESPONSE', response.status, data.error?.request_id ?? '', method === 'POST' && response.status >= 500);
      if (!data || !Object.hasOwn(data, 'data')) throw new ApiError('INVALID_RESPONSE', response.status, '', method === 'POST');
      return {...data, etag:response.headers.get('ETag')};
    } catch (error) {
      if (signal?.aborted) throw new DOMException('Aborted', 'AbortError');
      if (error instanceof ApiError) throw error;
      throw new ApiError(timeout.signal.aborted ? 'TIMEOUT' : 'NETWORK_ERROR', 0, '', method === 'POST');
    } finally { clearTimeout(timer); signal?.removeEventListener('abort', abort); }
  }
}
