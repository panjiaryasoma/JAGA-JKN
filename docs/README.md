# JAGA-JKN Documentation Hub

**Sistem Intelijen Kepatuhan Pemberi Kerja JKN** untuk **BPJS Kesehatan Healthkathon 2026**.

## Status proyek

- Repository scaffold: `ACCEPTED`
- Phase A — authority + discovery: `PASS_WITH_CONSTRAINTS`
- Business freeze: `NOT_STARTED`
- Preproduction: `HOLD`
- Implementation: `NOT_AUTHORIZED`

Phase A memvalidasi bahwa kategori **Efisiensi Risiko Pemberi Kerja** dan modus risikonya memang ditetapkan oleh penyelenggara, serta bahwa kewajiban pemberi kerja memiliki dasar regulasi. Phase A **tidak** membuktikan workflow internal BPJS, availability sumber data operasional, prevalence tiap modus, atau threshold domain produksi.

## Baseline konseptual

- Kategori: **Risiko Pemberi Kerja**
- Kandidat produk: **web decision-support internal BPJS Kesehatan, desktop-first responsive**
- Hipotesis solusi: expected/reference state → observed state → discrepancy → temporal episode → review/intervention → human decision → resolution/recurrence.
- Data prototipe: synthetic, seeded, versioned, validated.
- AI/ML tidak boleh menetapkan fraud, pelanggaran, utang, atau sanksi secara otomatis.

## Authority model

Status dokumen dan authority adalah dua hal berbeda. Folder atau nama file **tidak pernah** membuat sebuah artefak otomatis authoritative.

| Level | Authority | Contoh |
|---|---|---|
| A0 | Official competition / applicable law & regulation | Guide resmi, T&C resmi, peraturan |
| A1 | Approved project governance | Charter, scope, change control |
| A2 | Reviewed discovery / problem evidence | problem brief, discovery evidence |
| A3 | Frozen business/domain authority | BRD, business rules, domain policy |
| A4 | Frozen product/system/data architecture | PRD, SRS, data/ML requirements, architecture |
| A5 | Frozen implementation contracts | API/data/model/inference contracts |
| A6 | Verification/evidence/supporting artifacts | RTM, tests, acceptance evidence, submission mapping |

### Conflict rule

1. Higher authority level wins unless a formally approved change supersedes it.
2. A `DRAFT` document never overrides a `FROZEN` parent authority.
3. If two A0 sources conflict on mutable competition information such as dates, the newest official channel wins; the conflict must remain recorded.
4. If an implementation contract conflicts with a higher-level requirement, implementation is considered wrong until an approved change updates the higher-level authority.
5. Unknown facts remain `UNKNOWN`; they are not filled by assumption.

## DOCUMENT_MANIFEST.csv = control plane

`DOCUMENT_MANIFEST.csv` is the machine-readable registry for status, authority level, owner, and state. Metadata inside individual files must converge to the manifest before freeze.

The path `05_PREPRODUCTION/01_CONTRACTS_ACTIVE/` is legacy naming from the scaffold. Files inside it remain **inactive** while their manifest status is `DRAFT`. Path semantics do not override manifest state.

## Lifecycle

`DRAFT → REVIEWED → FROZEN → IMPLEMENTED → VERIFIED → ACCEPTED`

`SUPERSEDED` and `RETIRED` are terminal governance states for documents that no longer carry active authority.

## Next dependency

Phase B may now draft and review Charter → Scope → BRD → domain authority, but none may be frozen unless every material claim traces to Phase A evidence or is explicitly marked as an assumption.
