# Báo cáo cá nhân — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
|---|---|
| Họ và tên | Lê Hồ Quang Huy |
| MSSV | 2A202602026 |
| Khóa/Lớp | K4 |
| Tên nhóm | Abe |
| Vai trò chính | Thành viên 5: Integration & Comparison (phase1.py, corruption_flow.py) |
| Repository | https://github.com/tdattm/DAY10_2A202601678_NguyenTienDat |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

Tôi phụ trách tích hợp hai pipeline chính:

- Phase 1: ingestion → cleaning → embedding/index → frozen evaluation → quality/freshness → baseline report.
- Phase 2: corrupted data → corrupted evaluation → repair từ raw snapshot → repaired evaluation → comparison report.

| Module | Trách nhiệm | Artifact liên quan |
|---|---|---|
| `src/pipelines/phase1.py` | Điều phối baseline end-to-end | `data/results/baseline_metrics.json`, `data/reports/phase1_report.md` |
| `src/pipelines/corruption_flow.py` | Điều phối corruption, repair và comparison | `data/results/*_metrics.json`, `data/reports/corruption_report.md` |

## 3. Công việc đã thực hiện

### 3.1. Phase 1 orchestration

`phase1.py` thực hiện:

1. Load hoặc fetch raw records từ Crossref.
2. Chạy cleaning và lưu clean CSV/JSON.
3. Build Chroma index từ dữ liệu sạch.
4. Tạo hoặc sử dụng frozen evaluation set.
5. Chạy evaluation và lưu metrics/answers.
6. Chạy quality checks và freshness monitoring.
7. Sinh báo cáo baseline.

Embedding backend hiện tại sử dụng OpenAI `text-embedding-3-small`, được cấu hình qua `.env`.

### 3.2. Corruption và comparison orchestration

`corruption_flow.py` thực hiện:

1. Đọc `papers_clean_corrupted.csv`.
2. Rebuild index cho corrupted data.
3. Evaluate trên cùng frozen test set với baseline.
4. Chạy quality/freshness checks cho corrupted state.
5. Đọc lại `data/raw/crossref_records.json`.
6. Chạy lại cleaning chuẩn để repair dữ liệu.
7. Rebuild index và evaluate repaired state.
8. Sinh comparison report với ba cột Baseline / Corrupted / Repaired.

Repair không sử dụng lại corrupted dataframe và không fetch lại dữ liệu sống từ API. Điều này giúp thí nghiệm tái lập được trên cùng raw snapshot.

## 4. Cách chạy và xác minh

Từ project root:

```powershell
. .\.venv-win\Scripts\Activate.ps1
$env:PYTHONPATH = "$PWD\src"
python script\run_phase1.py
python script\run_corruption_flow.py
```

Các artifact cần kiểm tra:

```text
data/raw/crossref_response.json
data/raw/crossref_records.json
data/clean/papers_clean.csv
data/clean/papers_clean_corrupted.csv
data/clean/papers_clean_repaired.csv
data/eval/test_set.json
data/results/baseline_metrics.json
data/results/corrupted_metrics.json
data/results/repaired_metrics.json
data/results/corruption_log.json
data/reports/phase1_report.md
data/reports/corruption_report.md
```

## 5. Kết quả thực tế

Các trạng thái được đánh giá trên cùng frozen evaluation set gồm 17 câu hỏi.

| Metric | Baseline | Corrupted | Repaired |
|---|---:|---:|---:|
| `retrieval_hit_rate` | 1.000 | 1.000 | 1.000 |
| `mean_token_f1` | 0.750 | 0.690 | 0.750 |
| `judge_accuracy` | 0.706 | 0.647 | 0.706 |
| `mean_judge_score` | 4.176 | 3.941 | 4.235 |

Observability signals:

| Signal | Baseline | Corrupted | Repaired |
|---|---:|---:|---:|
| Quality overall | Pass | Fail | Pass |
| Duplicate IDs | 0 | 1 | 0 |
| Short summaries | 0 | 1 | 0 |
| Freshness | Pass | Fail | Pass |
| Stale rows | 0 | 1 | 0 |

## 6. Phân tích kết quả

Corruption làm giảm `mean_token_f1` từ `0.750` xuống `0.690` và `judge_accuracy` từ `0.706` xuống `0.647`. Điều này cho thấy dữ liệu lỗi ảnh hưởng đến chất lượng câu trả lời dù `retrieval_hit_rate` vẫn bằng 1.0.

`retrieval_hit_rate` chưa giảm vì corpus chỉ có 24 tài liệu và `top_k=4`, nên tài liệu đúng vẫn thường xuất hiện trong nhóm retrieved documents. Các chỉ số answer quality và quality/freshness phản ánh tác động rõ hơn.

Repair phục hồi metrics về mức baseline vì repair được thực hiện bằng cách đọc raw records và chạy lại đúng cleaning logic. Đây là kết quả mong đợi: cùng raw snapshot, cùng clean contract và cùng frozen test set phải cho trạng thái repaired gần với baseline.

Mean judge score của repaired cao hơn baseline một chút do LLM judge có thể không hoàn toàn deterministic.

## 7. Câu hỏi kỹ thuật

### Vì sao phải dùng cùng frozen test set?

Nếu mỗi trạng thái dùng một bộ câu hỏi khác nhau, thay đổi metrics có thể đến từ độ khó của câu hỏi thay vì corruption. Frozen set giúp so sánh công bằng giữa baseline, corrupted và repaired.

### Vì sao repair phải bắt đầu từ raw snapshot?

Nếu repair trực tiếp trên corrupted dataframe, các giá trị đã bị blank, stale hoặc nhiễu có thể tiếp tục tồn tại. Raw snapshot là nguồn dữ liệu gốc trước corruption; chạy lại cleaning từ nguồn này giúp khôi phục đúng schema và bảo đảm reproducibility.

### Kịch bản nào ảnh hưởng retrieval/answer quality rõ nhất?

Blank Summary và Add Noise ảnh hưởng trực tiếp đến nội dung được đưa vào embedding. Blank Summary làm mất thông tin trả lời, còn Add Noise làm giảm tín hiệu semantic. Stale Date chủ yếu ảnh hưởng freshness và câu hỏi ngày xuất bản; duplicate ảnh hưởng data quality và có thể làm phân bố retrieval bị lệch.

## 8. Khó khăn và giới hạn

- `retrieval_hit_rate` vẫn cao do corpus nhỏ và `top_k` tương đối lớn.
- Các metric judge có thể dao động nhẹ giữa các lần chạy vì LLM evaluator.

## 9. Tự đánh giá

- [x] Hiểu luồng end-to-end của Phase 1 và Phase 2.
- [x] Có thể giải thích input/output của `phase1.py` và `corruption_flow.py`.
- [x] Đối chiếu kết luận bằng metrics và artifacts thực tế.
- [x] Repair sử dụng raw snapshot thay vì corrupted dataframe.
- [x] Không ghi API key hoặc secret vào báo cáo.

**Họ và tên:** Lê Hồ Quang Huy  
**Ngày xác nhận:** 2026-08-06

