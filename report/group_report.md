# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin | Nội dung |
| --- | --- |
| Khóa/Lớp | K4 |
| Tên nhóm | Abe |
| Repository | [github.com/tdattm/DAY10_2A202601678_NguyenTienDat](https://github.com/tdattm/DAY10_2A202601678_NguyenTienDat) |
| Ngày hoàn thành | 2026-08-06 |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Nguyễn Tiến Đạt | 2A202601678 | Source Ingestion | `crossref.py`, raw response và raw records |
| 2 | Lã Phan Hoài An | 2A202601846 | Cleaning & Test Set | `cleaning.py`, `testset.py`, cleaned dataset và evaluation set |
| 3 | Nguyễn Nam Phong | 2A202601320 | Observability | `quality.py`, `reporting.py`, quality/freshness artifacts |
| 4 | Kiều Phúc Huy | 2A202601056 | Corruption Owner | `corruption.py`, corrupted dataset và `corruption_log.json` |
| 5 | Lê Hồ Quang Huy | 2A202602026 | Integration, Repair & Comparison | `phase1.py`, `corruption_flow.py`, repair từ raw, artifacts và metrics end-to-end |

## 2. Tóm tắt kết quả

Nhóm đã hoàn thành pipeline dữ liệu hai pha cho hệ thống RAG trên 24 bài báo lấy từ Crossref. Pha baseline lưu raw response và raw records, chuẩn hóa thành Clean Schema 10 cột, xây ba collection ChromaDB bằng `text-embedding-3-small`, đóng băng evaluation set 17 câu hỏi và tạo đầy đủ metrics, quality, freshness cùng báo cáo Markdown. Baseline đạt retrieval hit rate `1.0000`, mean token F1 `0.7504`, judge accuracy `0.7059` và mean judge score `4.1765`; quality và freshness đều Pass. Pha corruption chủ động làm rỗng summary, làm cũ ngày xuất bản, thêm duplicate và chèn noise vào các document thuộc frozen test set. Quality chuyển sang Fail, stale rows tăng từ 0 lên 1, token F1 giảm còn `0.6905`, judge accuracy còn `0.6471` và judge score còn `3.9412`; retrieval hit rate vẫn giữ `1.0000`, cho thấy corruption làm giảm chất lượng nội dung trả lời nhưng chưa làm mất document khỏi top-k. Repair đọc lại raw snapshot rồi chạy lại cleaning, đưa quality/freshness về Pass và phục hồi toàn bộ token F1, judge accuracy; judge score còn cao hơn baseline `0.0588`. Giới hạn chính là Crossref không trả category cho corpus hiện tại, Ragas chưa bật, và một số manifest/log chứa đường dẫn tuyệt đối từ máy đã chạy nên cần rebuild khi tái hiện trên máy khác.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref /works API
    -> raw response + parsed PaperRecord
    -> clean DataFrame (10-column contract)
    -> OpenAI text-embedding-3-small + ChromaDB
    -> frozen 17-question evaluation set
    -> baseline evaluation + quality/freshness reports
    -> controlled corruption on frozen-test documents
    -> corrupted index + re-evaluation
    -> repair from raw Crossref snapshot
    -> repaired index + re-evaluation
    -> baseline/corrupted/repaired comparison report
```

### Trách nhiệm của từng khối

| Khối | Input | Xử lý chính | Output/artifact | Owner |
| --- | --- | --- | --- | --- |
| Ingestion | Crossref `/works` | Query, retry/backoff, parse DOI/metadata, lưu snapshot | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Nguyễn Tiến Đạt |
| Cleaning | `list[PaperRecord]` | Chuẩn hóa text/list/ngày, validate, deduplicate, tạo embedding text | `data/clean/papers_clean.{csv,json}` | Lã Phan Hoài An |
| Evaluation set | Clean DataFrame | Chọn 6 paper mới nhất, tạo và đóng băng 17 câu factual | `data/eval/test_set.json` | Lã Phan Hoài An; thành viên 5 tích hợp/freeze |
| Embedding/index | Clean/corrupted/repaired DataFrame | OpenAI embeddings, ba Chroma collection riêng | `data/embeddings/*.json`, `data/chroma/` | Thành viên 5 |
| Evaluation | Frozen test set + index | Top-k retrieval, token F1, Gemini judge, optional Ragas | `data/results/*_metrics.json`, `*_answers.json` | Thành viên 5 |
| Observability | DataFrame của từng trạng thái | Null/unique/summary/freshness checks, Markdown reports | `data/quality/*.json`, `data/reports/*.md` | Nguyễn Nam Phong |
| Corruption | Baseline Clean DataFrame + frozen `test_set.json` document IDs | Tạo 4 scenario `blank_summary`, `stale_date`, `duplicate`, `add_noise`; nhắm vào document trong evaluation set và log từng thay đổi | `data/clean/papers_clean_corrupted.{csv,json}`, `data/results/corruption_log.json` | Kiều Phúc Huy |
| Repair/orchestration | Raw snapshot, corrupted dataset và toàn bộ module trên | Chạy hai pha, repair bằng cách clean lại raw records, rebuild index, evaluate và tạo comparison | Repaired dataset, metrics và report ba trạng thái | Lê Hồ Quang Huy |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình | Giá trị sử dụng |
| --- | --- |
| `LLM_PROVIDER` | `gemini` |
| `LLM_MODEL` | `gemini-2.5-flash` |
| Embedding model | `text-embedding-3-small` |
| Số lượng Crossref records | 24 |
| Retrieval `top_k` | 4 |
| Freshness threshold | 180 ngày |
| Baseline collection | `papers-baseline` |
| Corrupted collection | `papers-corrupted` |
| Repaired collection | `papers-repaired` |
| Random seed | Không sử dụng; test set chọn theo thứ tự xác định và được freeze |

Credential chỉ được đọc từ `.env`; báo cáo không chứa API key hoặc secret.

### Lệnh cài đặt đã sử dụng

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

Không cài riêng bằng `pip install -r requirements.txt`, vì cách đó không cài package trong `src/`.

### Lệnh chạy

```powershell
python script/run_phase1.py
python script/run_corruption_flow.py
```

### Kết quả tái hiện đã lưu

| Lệnh | Trạng thái | Thời điểm artifact gần nhất (ICT) | Bằng chứng |
| --- | --- | --- | --- |
| Baseline pipeline | Thành công | 2026-08-06 17:11 | `baseline_metrics.json`, `baseline_quality.json`, `freshness_report.json`, `phase1_report.md` |
| Corruption flow | Thành công | 2026-08-06 17:16 | `corrupted_metrics.json`, `repaired_metrics.json`, `corruption_log.json`, `corruption_report.md` |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính | Giá trị |
| --- | --- |
| Source | `https://api.crossref.org/works` |
| Query | `agentic retrieval augmented generation large language model` |
| Filter khi artifact được tạo | `from-pub-date:2026-02-07,has-abstract:true` |
| Thời điểm artifact được tạo | 2026-08-06 17:11 ICT |
| Số record nhận được | 24 |
| Cơ chế retry/backoff | Tối đa 4 lần cho HTTP 429/500/502/503/504; ưu tiên `Retry-After`, nếu không có dùng `2**attempt`, giới hạn 30 giây |

### Raw schema (`PaperRecord`)

| Trường | Kiểu | Bắt buộc? | Ý nghĩa/xử lý khi thiếu |
| --- | --- | --- | --- |
| `paper_id` | `str` | Có | DOI; record thiếu bị loại khi parse |
| `title` | `str` | Có | Tiêu đề; record thiếu bị loại khi parse |
| `summary` | `str` | Có cho Clean Schema | Abstract đã bỏ HTML; cleaning loại nếu ngắn dưới 100 ký tự |
| `authors` | `list[str]` | Không | Chuẩn hóa và nối thành `authors_joined` |
| `categories` | `list[str]` | Không | Chuẩn hóa và nối thành `categories_joined` |
| `primary_category` | `str` | Không | Category đầu tiên nếu có; không đưa vào Clean Schema |
| `published`, `updated` | `str` | `published` bắt buộc khi clean | Chấp nhận `YYYY`, `YYYY-MM`, `YYYY-MM-DD`; ngày lỗi bị loại |
| `abs_url`, `pdf_url`, `comment` | `str` | Không | Giữ URL cần thiết; trường tùy chọn có thể rỗng |

### Clean schema

| Trường | Kiểu | Bắt buộc? | Ý nghĩa/xử lý |
| --- | --- | --- | --- |
| `paper_id` | `str` | Có | DOI unique không phân biệt hoa/thường |
| `title` | `str` | Có | Bỏ HTML và chuẩn hóa khoảng trắng |
| `summary` | `str` | Có | Bỏ HTML, chuẩn hóa, tối thiểu 100 ký tự ở cleaning |
| `published` | `str` | Có | Chuẩn hóa `YYYY-MM-DD` |
| `authors_joined` | `str` | Không | Tác giả nối bằng `, ` |
| `categories_joined` | `str` | Không | Category nối bằng `, `; corpus hiện tại rỗng 24/24 |
| `age_days` | `int` | Có | Số ngày giữa thời điểm chạy và `published`, phải không âm |
| `text_for_embedding` | `str` | Có | `Title: ... | Authors: ... | Summary: ...` |
| `abs_url`, `pdf_url` | `str` | Không | URL nguồn/URL PDF nếu có |

### Quy tắc cleaning và kết quả

| Quy tắc | Quality dimension | Số record bị loại/thay đổi | Cách xác minh |
| --- | --- | ---: | --- |
| Loại thiếu DOI/title/summary hợp lệ | Completeness | 0 record bị loại trong lần chạy cuối | Raw 24 → clean 24 |
| Loại summary dưới 100 ký tự | Validity | 0 record bị loại | Clean row count 24 |
| Parse và chuẩn hóa ngày | Consistency | 1 ngày rút gọn được chuẩn hóa | So `crossref_records.json` với `papers_clean.csv` |
| Loại ngày lỗi hoặc ngày tương lai | Validity | 0 record bị loại | `age_days < 0`: 0 |
| Deduplicate DOI bằng `casefold()` | Uniqueness | 0 duplicate trong corpus cuối | `baseline_quality.json` |
| Chuẩn hóa authors/categories | Consistency | 24 records có authors; 0 có category | Clean CSV |

DOI từ Crossref được giữ làm document identity xuyên suốt raw, clean, Chroma metadata và `ground_truth_doc_ids`. `age_days` được tính sau khi đưa ngày về mốc không timezone. Text embedding ghép title, authors và summary bằng nhãn ổn định để retrieval khai thác cả chủ đề lẫn nội dung.

## 6. Evaluation setup

| Thành phần | Cấu hình thực tế |
| --- | --- |
| Số câu hỏi | 17 |
| `question_type` | `factual` (17/17) |
| Số ground-truth documents | 6 DOI duy nhất |
| Ground-truth document ID | DOI trong Clean Schema, lưu dưới `ground_truth_doc_ids` |
| Nội dung câu hỏi | Authors, ngày xuất bản, vấn đề/ứng dụng; category chỉ tạo khi nguồn có dữ liệu |
| Embedding model | `text-embedding-3-small` |
| Vector store | ChromaDB cosine; ba collection baseline/corrupted/repaired |
| Retrieval `top_k` | 4 |
| LLM judge | Gemini `gemini-2.5-flash`; 0/17 fallback judge trong cả ba trạng thái |
| Frozen test set | `data/eval/test_set.json` |

Test set được tạo theo thứ tự mới nhất và lưu cố định. Corruption flow đọc lại đúng file này thay vì sinh câu hỏi mới; do đó cả ba trạng thái dùng cùng 17 câu, cùng ground truth và cùng DOI. Cách này cô lập tác động của thay đổi dữ liệu khỏi thay đổi đề đánh giá.

## 7. Kết quả baseline

### Artifact checklist

| Artifact | Đường dẫn | Trạng thái | Ghi chú |
| --- | --- | --- | --- |
| Raw response/records | `data/raw/` | Có | 24 parsed records |
| Cleaned dataset | `data/clean/papers_clean.{csv,json}` | Có | 24 records, 10 cột |
| Embedding manifest/index | `data/embeddings/papers_embeddings.json`, `data/chroma/` | Có | 24 documents, `papers-baseline` |
| Evaluation set | `data/eval/test_set.json` | Có | 17 câu, 6 DOI |
| Baseline metrics/answers | `data/results/baseline_*.json` | Có | 17 answers |
| Quality/freshness | `data/quality/baseline_quality.json`, `freshness_report.json` | Có | Pass/Pass |
| Baseline report | `data/reports/phase1_report.md` | Có | Khớp metrics JSON |

### Baseline metrics

| Metric | Giá trị | Diễn giải |
| --- | ---: | --- |
| `retrieval_hit_rate` | 1.0000 | Cả 17 câu đều retrieve được ít nhất một ground-truth DOI trong top-k |
| `mean_token_f1` | 0.7504 | Mức trùng token trung bình giữa answer và ground truth |
| `judge_accuracy` | 0.7059 | 12/17 câu được judge đánh giá materially correct |
| `mean_judge_score` | 4.1765/5 | Điểm judge trung bình cao dù một số answer chưa khớp hoàn toàn |
| Ragas | Không chạy | Mặc định bỏ qua; cần đặt `RUN_RAGAS=1` để bật lượt đánh giá chậm hơn |

## 8. Data quality và freshness

### Quality checks

| Check | Quality dimension | Ngưỡng/kỳ vọng | Baseline | Corrupted | Repaired |
| --- | --- | --- | ---: | ---: | ---: |
| Row count | Volume | Dataset không rỗng | 24 | 25 | 24 |
| Null `paper_id` | Completeness | 0 | 0 (Pass) | 0 | 0 (Pass) |
| Duplicate `paper_id` | Uniqueness | 0 | 0 (Pass) | 1 (Fail) | 0 (Pass) |
| Null `title` | Completeness | 0 | 0 (Pass) | 0 (Pass) | 0 (Pass) |
| Summary dưới 10 ký tự | Validity | 0 | 0 (Pass) | 1 (Fail) | 0 (Pass) |
| `age_days > 180` | Freshness | 0 | 0 (Pass) | 1 (Fail) | 0 (Pass) |
| Overall | Tổng hợp | Tất cả check Pass | Pass | Fail | Pass |

### Freshness

| Thuộc tính | Baseline | Corrupted | Repaired |
| --- | --- | --- | --- |
| Latest published | 2026-08-05 | 2026-08-05 | 2026-08-05 |
| Oldest published | 2026-02-12 | 2000-01-01 | 2026-02-12 |
| Stale rows / total | 0/24 | 1/25 | 0/24 |
| Ngưỡng | 180 ngày | 180 ngày | 180 ngày |
| Trạng thái | Fresh | Stale | Fresh |

## 9. Corruption scenarios và repair

| Corruption | Cách tạo | Record tác động | Quality signal | Tác động thực tế | Repair |
| --- | --- | ---: | --- | --- | --- |
| Blank summary | Đặt summary thành chuỗi rỗng | 1 | Short summary tăng | 0 → 1; token/answer metrics giảm | Re-clean raw record |
| Stale date | Đổi `2026-07-13` thành `2000-01-01`, refresh `age_days` | 1 | Stale rows tăng | 0 → 1; freshness Fail | Khôi phục ngày từ raw |
| Duplicate | Sao chép row và giữ nguyên DOI | 1 row thêm | Duplicate ID tăng | Row 24 → 25; duplicate 0 → 1 | Rebuild clean dataset từ raw 24 records |
| Add noise | Thêm marker unrelated weather vào `text_for_embedding` | 1 | Retrieval/content relevance | Hit rate không đổi, nhưng answer metrics tổng thể giảm cùng corruption set | Tạo lại embedding text từ raw-clean |

Corruption log tồn tại tại `data/results/corruption_log.json`, ghi frozen IDs, các DOI bị tác động, giá trị trước/sau và row count. Ba DOI bị sửa đều thuộc frozen evaluation set nên corruption có khả năng quan sát được qua cùng bộ đánh giá.

Repair không chỉnh trực tiếp corrupted CSV. Pipeline đọc `data/raw/crossref_records.json`, chạy lại `build_clean_dataframe`, ghi repaired CSV/JSON, rebuild collection `papers-repaired`, rồi đánh giá lại bằng frozen test set. Vì nguồn repair là raw snapshot bất biến nên các lỗi phát sinh trong derived clean dataset không được giữ lại.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.0000 | 1.0000 | 1.0000 | 0.0000 | Không cần phục hồi | Corruption không xóa DOI khỏi top-k |
| `mean_token_f1` | 0.7504 | 0.6905 | 0.7504 | -0.0599 | 100% | Phục hồi đúng baseline |
| `judge_accuracy` | 0.7059 | 0.6471 | 0.7059 | -0.0588 | 100% | Phục hồi đúng baseline |
| `mean_judge_score` | 4.1765 | 3.9412 | 4.2353 | -0.2353 | 125% khoảng giảm | Repaired cao hơn baseline 0.0588 do judge LLM có biến thiên |
| Quality overall | Pass | Fail | Pass | Pass → Fail | Đầy đủ | Duplicate, blank summary và stale date đều được loại bỏ |
| Freshness | Fresh | Stale | Fresh | 0 → 1 stale row | Đầy đủ | Oldest date trở lại 2026-02-12 |

Hai kết luận nhân quả dựa trên artifacts:

1. Blank summary + noise trên document thuộc frozen test set làm quality Fail và giảm thông tin hữu ích trong context; dù DOI vẫn được retrieve (`hit_rate = 1.0`), mean token F1 giảm `0.0599`, judge accuracy giảm `0.0588` và mean judge score giảm `0.2353`. Điều này cho thấy retrieval hit đơn thuần chưa đủ bảo đảm answer quality.
2. Repair từ raw snapshot loại duplicate, khôi phục summary/ngày và rebuild index; quality/freshness trở lại Pass/Fresh, token F1 và judge accuracy trở về đúng baseline. Judge score nhỉnh hơn baseline `0.0588`, phù hợp với biến thiên của LLM judge hơn là thay đổi dữ liệu, vì deterministic token F1 đã phục hồi chính xác.

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** Corpus Crossref cuối có `categories_joined` rỗng ở cả 24 records, nên không thể tạo ground truth category đáng tin cậy; test set thử nghiệm ban đầu chỉ có 12 câu thuộc ba nhóm summary/authors/date.
- **Nguyên nhân:** Trường `subject` của Crossref không có dữ liệu cho query và tập 24 records hiện tại.
- **Cách xử lý:** Không tạo category giả. Integration mở rộng tập paper được chọn lên 6, chuẩn hóa các câu thành `factual`, tạo câu authors/date/application từ metadata thật và freeze đúng 17 câu.
- **Cách xác minh:** `data/eval/test_set.json` có 17 sample, 6 DOI duy nhất; cả ba file metrics đều có `samples = 17`.

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng | Hướng cải thiện có thể kiểm chứng |
| --- | --- | --- |
| Crossref không trả category cho 24/24 records | Không đo được câu hỏi category | Đổi query/mở rộng corpus, chỉ thêm category question khi ground truth không rỗng |
| Ragas chưa chạy | Chưa có faithfulness/context precision/context recall | Đặt `RUN_RAGAS=1`, chạy lại ba trạng thái cùng cấu hình và lưu metrics |
| Embedding dùng API bên ngoài | Cần network/key và có chi phí | Ghi rõ provider; thêm lựa chọn MiniLM local và so sánh retrieval trên cùng test set |
| Manifest/log lưu đường dẫn tuyệt đối của máy tạo artifact | `LocalEmbeddingIndex.load()` có thể không portable sang máy khác | Lưu path tương đối với project hoặc resolve lại qua `Settings.paths.chroma_dir`; rebuild trên máy sạch để xác minh |
| LLM judge có biến thiên | Repaired judge score có thể khác baseline dù answers tương đương | Lưu raw judge answers, chạy lặp hoặc bổ sung deterministic metric/seed nếu provider hỗ trợ |
| Corruption chưa xóa document khỏi index | Retrieval hit rate không giảm | Thêm scenario drop ground-truth record và đối chiếu hit-rate trên frozen set |

## 13. Checklist trước khi nộp

- [x] Họ tên và MSSV của 5 thành viên đã được nhóm xác nhận và điền đầy đủ.
- [x] Repository, lớp, tên nhóm và phân công kỹ thuật khớp bằng chứng hiện có.
- [x] Baseline và corruption flow có đầy đủ artifact đầu ra.
- [x] Baseline, corrupted và repaired dùng cùng evaluation set 17 câu.
- [x] Bảng metrics khớp `data/results/*_metrics.json`.
- [x] Quality/freshness conclusions khớp `data/quality/*.json`.
- [x] Các đường dẫn report và artifact tồn tại trong repository.
- [x] Tất cả 5 thành viên đã có individual report trong `report/`.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
