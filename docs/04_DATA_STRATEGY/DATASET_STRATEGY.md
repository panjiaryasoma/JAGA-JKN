---
project: JAGA-JKN
competition: BPJS Kesehatan Healthkathon 2026
status: DRAFT
version: 0.1.0
owner: Lintang
authority: Data Strategy
last_updated: 2026-10-07
---

# Dataset Strategy

## Prinsip
Dataset prototipe menggunakan **two-world synthetic design**.

### True / Reference World
Merepresentasikan kondisi tenaga kerja dan kewajiban yang dianggap benar dalam simulasi.

### Observed World
Merepresentasikan kondisi yang tercatat/dilaporkan ke sistem JKN dalam simulasi.

Risk episode lahir dari divergence terkontrol antara dua dunia tersebut, bukan dari label random.

## Reproducibility
- `generation_seed = 20261006`
- `split_seed = 20261007`
- `model_seed = 20261008`
- Dataset freeze memiliki version + SHA-256 + generator commit SHA.

## Grain
- Raw: worker/employer/event/month.
- Model/evaluation: employer-period dan episode.

## Caveat
Performa pada synthetic ground truth **tidak membuktikan** performa pada data operasional BPJS. Validasi pada authorized anonymized data diperlukan sebelum production use.
