# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                                                                                                     |
| ------------------ | ------------------------------------------------------------------------------------------------------------- |
| Họ và tên       | Kiều Phúc Huy                                                                                                |
| MSSV               | 2A202601056                                                                                                    |
| Khóa/Lớp         | K4                                                                                                             |
| Tên nhóm         | Abe                                                                                                            |
| Vai trò chính    | Corruption owner (`src/ingestion/corruption.py`)                                                             |
| Repository         | [github.com/tdattm/DAY10_2A202601678_NguyenTienDat](https://github.com/tdattm/DAY10_2A202601678_NguyenTienDat) |
| Ngày hoàn thành | 2026-08-06                                                                                                    |


## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable         | File/hàm phụ trách                                       | Input nhận vào                                             | Output bàn giao                                                                                  | Trạng thái |
| --------------------------- | ------------------------------------------------------------ | -------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- | ------------ |
| Corruption scenarios        | `src/ingestion/corruption.py` (`corrupt_clean_dataframe`) | `df: pd.DataFrame` (cleaned dataset), `output_log_path` | `DataFrame` đã corrupt + `data/clean/papers_clean_corrupted.csv`/`.json` + corruption log JSON | Hoàn thành |
| Corruption log               | Cùng hàm `corrupt_clean_dataframe`                          | Danh sách `frozen_test_set_doc_ids` đọc từ `data/eval/test_set.json` | `data/results/corruption_log.json` mô tả từng scenario và document bị tác động              | Hoàn thành |

### Việc ngoài phạm vi (chưa đảm nhận)

| Phần                                     | Owner theo phân công    | Lý do chưa làm ở đây |
| ------------------------------------------ | -------------------------- | ------------------------ |
| Ghép corruption → evaluate → repair → compare | Thành viên 5 (`phase1.py`, `corruption_flow.py`) | `corruption_flow.py` hiện vẫn `raise NotImplementedError`, chưa được nhóm hoàn thiện tại thời điểm viết báo cáo này |
| Logic repair từ raw records                 | Thành viên 5              | Repair không nằm trong `corruption.py`; hàm của tôi chỉ tạo corrupted data, không tự phục hồi |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                              | Thành viên/module được hỗ trợ | Kết quả                                                             |
| ---------------------------------------- | ------------------------------------ | ---------------------------------------------------------------------- |
| Thống nhất document identity (`paper_id`) | Thành viên 2 (Cleaning)              | Dùng chung `paper_id` để map corruption vào đúng document trong eval set |
| Đọc `ground_truth_doc_ids` từ eval set | Thành viên 3 (Evaluation)            | Corruption cố tình nhắm vào các `paper_id` nằm trong test set để đảm bảo impact đo được |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện                       | File/hàm/artifact liên quan                                    | Kết quả bàn giao                                                                | Cách xác minh                                                          |
| ---------------------------------------------- | ------------------------------------------------------------------ | ---------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| Implement `corrupt_clean_dataframe`          | `src/ingestion/corruption.py`                                    | Hàm nhận cleaned `DataFrame`, trả về `DataFrame` đã corrupt theo 4 scenario | Gọi trực tiếp hàm với `clean_df` đã build từ `build_clean_dataframe` |
| Validate input trước khi corrupt            | `src/ingestion/corruption.py` (đầu hàm)                        | Raise `ValueError` nếu thiếu cột bắt buộc hoặc `df` rỗng                    | Test gọi hàm với `DataFrame` thiếu cột `summary`                     |
| Ghi corrupted dataset và corruption log      | `_rebuild_embedding_text`, `write_json`                         | `data/clean/papers_clean_corrupted.csv/json`, `data/results/corruption_log.json` | Mở các file JSON/CSV trong `data/clean/` và `data/results/`          |

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Nhiệm vụ của tôi là tạo ra các lỗi dữ liệu **có chủ đích và đo được**, không phải lỗi ngẫu nhiên. Corruption phải trùng với các document nằm trong evaluation set (frozen test set) để khi Thành viên 5 chạy lại evaluation trên dữ liệu bẩn, số liệu (`retrieval_hit_rate`, `mean_token_f1`, ...) chắc chắn thay đổi và có thể quy trách nhiệm rõ ràng cho từng loại lỗi.

### Cách triển khai

`corrupt_clean_dataframe(df, output_log_path)` thực hiện các bước:

1. **Validate input**: kiểm tra đủ 6 cột bắt buộc (`paper_id`, `title`, `summary`, `published`, `authors_joined`, `text_for_embedding`) và `df` không rỗng, raise `ValueError` sớm nếu sai contract.
2. **Đọc `frozen_test_set_doc_ids`** từ `data/eval/test_set.json` (hàm nội bộ `_frozen_doc_ids`) để lấy danh sách `paper_id` đang được dùng làm ground truth. Nếu không đọc được test set (chưa tồn tại hoặc lỗi parse), fallback về document đầu tiên trong `df` để hàm vẫn chạy được độc lập.
3. **Chọn record mục tiêu** bằng round-robin trên danh sách `target_ids` (hàm `index_for`), đảm bảo mỗi corruption scenario nhắm vào một document có trong eval set thay vì random toàn bộ dataset.
4. **Áp dụng 4 corruption scenario**, mỗi scenario được log lại thành một entry có `scenario`, `paper_ids`, `changed_fields`:
   - `blank_summary`: xóa trắng `summary` của một document (mô phỏng thiếu nội dung).
   - `stale_date`: đổi `published` thành `2000-01-01` (mô phỏng dữ liệu cũ, phục vụ freshness check).
   - `duplicate`: nhân đôi một dòng bằng `pd.concat`, giữ nguyên `paper_id` (mô phỏng duplicate record).
   - `add_noise`: rebuild lại `text_for_embedding` qua `_rebuild_embedding_text`, sau đó nối thêm chuỗi rác `[NOISE::unrelated_weather_report_7f3a]` (mô phỏng nhiễu văn bản ảnh hưởng embedding/retrieval).
5. **Ghi artifact**: lưu `DataFrame` đã corrupt ra `papers_clean_corrupted.csv/json`, và ghi `corruption_log.json` chứa nguồn gốc, danh sách `overlap_doc_ids` (giao giữa các document bị sửa và frozen test set), số dòng trước/sau, chi tiết từng scenario và đường dẫn artifact — dùng `read_json`/`write_json` từ `core/utils.py`.

### Input, output và contract

| Thành phần               | Mô tả                                                                                                     |
| --------------------------- | ------------------------------------------------------------------------------------------------------------- |
| Input                       | `pd.DataFrame` đã qua `cleaning.py` (đủ 6 cột bắt buộc) + đường dẫn `output_log_path` để ghi log |
| Output                      | `DataFrame` corrupted (trả về trong process) + file CSV/JSON corrupted + `corruption_log.json`          |
| Module phụ thuộc          | `cleaning.py` (schema đầu vào), `testset.py`/`data/eval/test_set.json` (để biết corrupt trúng document nào) |
| Module dự kiến sử dụng output | `corruption_flow.py` (chưa hoàn thiện) — sẽ đọc `DataFrame` corrupted để rebuild index và evaluate lại   |
| Điều kiện lỗi cần xử lý | Thiếu cột bắt buộc → `ValueError`; `df` rỗng → `ValueError`; thiếu `test_set.json` → fallback không crash |

### Cách xác minh

Vì `corruption_flow.py` chưa được nhóm hoàn thiện, tôi xác minh hàm ở mức đơn vị bằng cách gọi trực tiếp với `DataFrame` lấy từ `data/clean/papers_clean.json` (baseline đã chạy) và `output_log_path = data/results/corruption_log.json`:

```bash
uv run python -c "
import pandas as pd
from pathlib import Path
from ingestion.corruption import corrupt_clean_dataframe

df = pd.read_json('data/clean/papers_clean.json')
corrupted = corrupt_clean_dataframe(df, Path('data/results/corruption_log.json'))
print(corrupted.shape, df.shape)
"
```

- **Kết quả quan sát được:** `data/results/corruption_log.json` được sinh ra với 4 scenario, `overlap_doc_ids` khớp cả 3 document trong `frozen_test_set_doc_ids`, `corrupted_row_count = 25` so với `original_row_count = 24` (do scenario `duplicate`). File `papers_clean_corrupted.csv/json` cũng được ghi đúng cột.
- **Giới hạn của cách xác minh này:** đây là chạy thủ công hàm đơn lẻ, **không phải** chạy qua `script/run_corruption_flow.py` (script đó gọi `pipelines.corruption_flow.main`, hiện vẫn `raise NotImplementedError`). Vì vậy tôi **không** báo cáo rằng corruption flow đã chạy end-to-end, và cũng chưa có `corrupted_metrics.json`/`repaired_metrics.json`/`data/reports/corruption_report.md` để so sánh 3 trạng thái — các artifact này phụ thuộc vào phần việc của Thành viên 5.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Chọn document nào để corrupt — random trên toàn bộ dataset hay nhắm có chủ đích vào document đang nằm trong evaluation set.
- **Các phương án đã cân nhắc:** (a) Corrupt ngẫu nhiên bằng `df.sample()`; (b) Corrupt có chủ đích, ưu tiên document nằm trong `ground_truth_doc_ids` của `test_set.json`.
- **Phương án đã chọn:** (b) — đọc `frozen_test_set_doc_ids` và round-robin chọn document mục tiêu trong tập đó, chỉ fallback về document đầu tiên khi không đọc được test set.
- **Lý do:** Nếu corrupt ngẫu nhiên, có xác suất không document nào bị sửa trùng với evaluation set, khiến metrics baseline vs corrupted không đổi và không chứng minh được tác động của lỗi dữ liệu — vi phạm đúng mục tiêu của bài lab (rubric mục 8 yêu cầu "đo được impact rõ").
- **Bằng chứng quyết định phù hợp:** `corruption_log.json` cho thấy `overlap_doc_ids` trùng cả 3/3 document trong `frozen_test_set_doc_ids`, nghĩa là cả 3 ground-truth document của eval set đều bị ít nhất một loại corruption tác động.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** Nếu gọi hàm khi `data/eval/test_set.json` chưa tồn tại (ví dụ chạy trước khi Thành viên 3 tạo eval set), hàm ban đầu sẽ crash khi đọc file.
- **Nguyên nhân:** `_frozen_doc_ids` không kiểm tra sự tồn tại của file trước khi đọc.
- **Cách xử lý:** Thêm `if not test_set_path.exists(): return []` và bọc `read_json` trong `try/except (OSError, ValueError)`, đồng thời ở `corrupt_clean_dataframe` có fallback `target_ids = [str(corrupted.iloc[0]["paper_id"])]` khi không lấy được frozen ID nào — hàm vẫn tạo được corruption có chủ đích trên ít nhất một document thay vì crash toàn bộ.
- **Cách xác minh:** Gọi thử hàm với `output_log_path` trỏ tới thư mục không có `eval/test_set.json`, xác nhận hàm chạy xong và trả về `DataFrame` thay vì raise exception.

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?** `crossref.py` fetch và lưu raw records → `cleaning.py` chuẩn hóa, tạo `text_for_embedding` và `paper_id` → `retrieval/index.py` build embedding và nạp vào ChromaDB.
2. **Corruption tác động vào bước nào của pipeline?** Corruption chèn vào **sau** cleaning và **trước** khi re-index: nó nhận `DataFrame` đã sạch, sửa trực tiếp trên bản copy, rồi hàm `_rebuild_embedding_text` tái tạo lại `text_for_embedding` để đảm bảo các thay đổi (summary rỗng, noise) được phản ánh đúng khi index lại — nếu không rebuild, embedding cũ vẫn "sạch" dù field gốc đã bị sửa.
3. **Vì sao corruption phải nhắm vào document trong evaluation set thay vì random?** Vì evaluation set (`ground_truth_doc_ids`) là thứ duy nhất được dùng để tính `retrieval_hit_rate`/`mean_token_f1`. Corrupt ngoài phạm vi test set sẽ làm dữ liệu "bẩn" nhưng không ai đo được ảnh hưởng lên metric.
4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?** Để cô lập biến số duy nhất là chất lượng dữ liệu; nếu đổi test set giữa các lần chạy, chênh lệch metric có thể do câu hỏi khác nhau chứ không phải do corruption/repair.
5. **Repair (theo thiết kế, dù chưa implement trong repo) cần dựa vào nguồn nào để được coi là hợp lệ?** Repair phải load lại từ `data/raw/crossref_records.json` (raw records gốc, chưa qua corruption) và chạy lại `cleaning.py`, không được "sửa tay" trên bản corrupted — nếu không, kết quả repair chỉ che triệu chứng chứ không chứng minh khả năng phục hồi từ nguồn đáng tin cậy.

## 8. Phân tích kết quả

Vì `corruption_flow.py` chưa được implement, nhóm **chưa có** `corrupted_metrics.json`, `repaired_metrics.json` và `data/reports/corruption_report.md` để so sánh 3 trạng thái baseline/corrupted/repaired bằng agent metrics. Phần dưới đây chỉ phản ánh những gì `corrupt_clean_dataframe` tạo ra được, đối chiếu với baseline đã có.

| Artifact                                  | Trạng thái | Ghi chú                                                                |
| ------------------------------------------ | ------------ | -------------------------------------------------------------------------- |
| `data/results/baseline_metrics.json`     | Có         | `retrieval_hit_rate = 1.0`, `mean_token_f1 ≈ 0.750`, `judge_accuracy ≈ 0.706`, `mean_judge_score ≈ 4.18` (17 samples) |
| `data/results/corruption_log.json`       | Có         | 4 scenario, `original_row_count = 24` → `corrupted_row_count = 25`, `overlap_doc_ids` trùng cả 3 ground-truth doc IDs |
| `data/clean/papers_clean_corrupted.csv/json` | Có     | Sinh ra khi chạy thử hàm độc lập                                        |
| `data/results/corrupted_metrics.json`    | Thiếu     | Cần `corruption_flow.py` rebuild index trên dữ liệu corrupted rồi evaluate lại — chưa implement |
| `data/results/repaired_metrics.json`     | Thiếu     | Cần logic repair từ raw + evaluate lại — chưa implement                |
| `data/reports/corruption_report.md`      | Thiếu     | Cần `generate_corruption_report` (đã có sẵn trong `reporting.py`) được gọi từ `corruption_flow.py` |

### Kết luận từ số liệu hiện có

1. **Corruption có chủ đích trúng mục tiêu** → cả 3/3 document trong `ground_truth_doc_ids` của test set đều nằm trong `overlap_doc_ids`, nên về mặt thiết kế, nếu evaluate lại trên `papers_clean_corrupted.json`, `retrieval_hit_rate` và `mean_token_f1` được kỳ vọng giảm so với baseline (1.0 và ~0.750).
2. **Chưa thể kết luận về repair** vì repair chưa được implement trong repo tại thời điểm báo cáo — đây là giới hạn tôi chủ động ghi nhận thay vì suy đoán số liệu.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Corruption "ngẫu nhiên" không có giá trị đánh giá nếu không đảm bảo nó tác động lên đúng document đang được đo — phải neo corruption vào evaluation set.
2. Validate input sớm (`required_columns`, `df.empty`) giúp lỗi lộ ra ngay ở `corruption.py` thay vì lan xuống bước index/evaluate rồi mới phát hiện.
3. Một module nhỏ vẫn cần contract rõ ràng với các module khác (ở đây là schema của `cleaning.py` và cấu trúc `test_set.json` của `testset.py`) — tôi không tự đổi tên cột hay format log để tránh phá vỡ phần của Thành viên 5.

### Nếu có thêm thời gian

Tôi muốn thêm scenario "missing record" (drop hẳn một document khỏi dataset thay vì chỉ sửa field) như pseudo-code gốc gợi ý ("Drop mot so latest records"), và phối hợp với Thành viên 5 để hoàn thiện `corruption_flow.py` nhằm có đủ `corrupted_metrics.json`/`repaired_metrics.json` cho phần so sánh 3 trạng thái.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng (corruption flow end-to-end, repair, comparison report đều được ghi rõ là chưa hoàn thành).
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Kiều Phúc Huy
**Ngày xác nhận:** 2026-08-06
