# Phase 2: Corruption, Repair & Comparison

## Evaluation metrics

| Metric | Baseline | Corrupted | Repaired |
|---|---:|---:|---:|
| Retrieval hit rate | 1.0 | 1.0 | 1.0 |
| Mean token F1 | 0.7503673937474197 | 0.6904591751408281 | 0.7503673937474197 |
| Judge accuracy | 0.7058823529411765 | 0.6470588235294118 | 0.7058823529411765 |
| Mean judge score | 4.176470588235294 | 3.9411764705882355 | 4.235294117647059 |

## Data quality and freshness

| Signal | Baseline | Corrupted | Repaired |
|---|---:|---:|---:|
| Quality overall passed | True | False | True |
| Duplicate IDs | 0 | 1 | 0 |
| Short summaries | 0 | 1 | 0 |
| Freshness passed | True | False | True |
| Stale rows | 0 | 1 | 0 |

## Interpretation

The corrupted state intentionally modifies records used by the frozen evaluation
set. Repair starts from `data/raw/crossref_records.json` and reruns the standard
cleaning logic, so it does not preserve corruption from the derived clean file.
