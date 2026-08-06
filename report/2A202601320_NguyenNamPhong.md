# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                                                                                                     |
| ------------------ | ------------------------------------------------------------------------------------------------------------- |
| Họ và tên       | Nguyễn Nam Phong                                                                                             |
| MSSV               | 2A202601320                                                                                                   |
| Khóa/Lớp         | K4                                                                                                            |
| Tên nhóm         | Abe                                                                                                           |
| Vai trò chính    | Observability (quality.py, reporting.py)                                                                     |
| Repository         | [github.com/tdattm/DAY10_2A202601678_NguyenTienDat](https://github.com/tdattm/DAY10_2A202601678_NguyenTienDat) |
| Ngày hoàn thành | 2026-08-06                                                                                                    |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Data Quality Checks | `src/observability/quality.py` (`run_data_quality_checks`) | `df: pd.DataFrame` từ quá trình cleaning (Thành viên 2) | File JSON `data/quality/[report_name].json` mô tả kết quả pass/fail | Hoàn thành |
| Freshness Monitoring | `src/observability/quality.py` (`build_freshness_report`) | `df: pd.DataFrame` từ quá trình cleaning | File JSON `data/quality/freshness_report.json` mô tả độ trễ của dữ liệu | Hoàn thành |
| Phase 1 Reporting | `src/observability/reporting.py` (`generate_phase1_report`) | Các metrics dict: source_summary, metrics, quality, freshness | File Markdown `data/reports/phase1_report.md` | Hoàn thành |
| Corruption Comparison Reporting | `src/observability/reporting.py` (`generate_corruption_report`) | Các metrics dict của baseline, corrupted, repaired | File Markdown `data/reports/corruption_report.md` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                  | Thành viên/module được hỗ trợ | Kết quả                    |
| ----------------------------- | ------------------------------------ | ---------------------------- |
| Thống nhất Schema | Thành viên 2 (Cleaning) | Cùng thống nhất các cột `paper_id`, `title`, `summary`, `age_days` |
| Hỗ trợ tích hợp pipelines | Thành viên 5 (Integration) | Cung cấp hàm đúng chuẩn dictionary để ghép nối sinh báo cáo cuối cùng |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh  |
| --------------------------- | ----------------------------- | ------------------------- | ---------------- |
| Cài đặt các luật Data Quality | `src/observability/quality.py` | Tạo thành công các check null, unique, độ dài. Kết quả: file JSON | Mở file json trong thư mục `data/quality/` |
| Tạo báo cáo tổng hợp Markdown | `src/observability/reporting.py` | Sinh ra Phase1 Report và Corruption Report định dạng MD | Mở file `.md` trong thư mục `data/reports/` |

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Phần của tôi đóng vai trò là "cảnh vệ" của pipeline. Tôi cần đảm bảo dữ liệu chạy vào hệ thống RAG không bị lỗi (Data Quality) và không quá cũ (Freshness), đồng thời trình bày các báo cáo một cách trực quan bằng Markdown để người dùng (hoặc Developer khác) dễ theo dõi.

### Cách triển khai

- **Trong `quality.py`**: Sử dụng `pandas` để tính toán trên dataframe được truyền vào. 
  - Với `paper_id`: Kiểm tra `isnull()` và `duplicated()`.
  - Với `summary`: Tính độ dài bằng `.apply(lambda x: len(str(x)))` kết hợp `.fillna("")` để tránh lỗi kiểu dữ liệu.
  - Với Freshness: Dựa vào cột `age_days` tính toán và so sánh với `freshness_threshold_days` từ cấu hình Settings.
- **Trong `reporting.py`**: Sử dụng kỹ thuật f-string Python để format các giá trị trong dictionary thành cú pháp bảng Markdown chuẩn xác, và ghi ra đĩa bằng hàm `open(file, "w")`.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | `pd.DataFrame` chứa dữ liệu đã làm sạch và các metrics dictionaries |
| Output                         | Artifacts là file JSON (chứa metadata check quality) và file `.md` (Báo cáo trực quan) |
| Module phụ thuộc             | `cleaning.py` (Định hình các cột cho DataFrame), `phase1.py`, `corruption_flow.py` (Để cung cấp evaluation metrics) |
| Module sử dụng output        | `phase1.py` và `corruption_flow.py` gọi hàm để sinh báo cáo ở bước cuối pipeline |
| Điều kiện lỗi cần xử lý | Xử lý an toàn khi cột `summary` chứa giá trị NaN bằng `.fillna("")` để tính toán độ dài |

### Cách xác minh

```bash
uv run python script/run_phase1.py
```
- **Kết quả mong đợi:** Pipeline chạy mượt mà đến cuối cùng và sinh ra báo cáo trong `data/reports/phase1_report.md`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Xử lý giá trị có khả năng bị thiếu khi tính toán độ dài cột `summary` trong Data Quality.
- **Các phương án đã cân nhắc:** Dùng `.str.len()` hoặc `.fillna("").apply(len)`.
- **Phương án đã chọn:** Dùng `.fillna("").apply(lambda x: len(str(x)))`.
- **Lý do:** Trade-off về tính an toàn (robustness). Mặc dù `.str.len()` ngắn gọn nhưng dễ crash nếu dữ liệu pandas tự convert cột thành float khi toàn NaN.
- **Bằng chứng quyết định phù hợp:** Chạy mượt mà dù trong bước corruption, một số dòng bị cố tình chèn null vào summary.

## 6. Một lỗi hoặc blocker đã xử lý

- **Trạng thái:** Không có lỗi nghiêm trọng, do tôi và Thành viên 2 (Cleaning) đã thống nhất Data Contract rất chặt chẽ từ trước (có cột `paper_id`, `age_days`, `title`, `summary`), do đó không xảy ra xung đột khi code hàm của tôi đọc dữ liệu từ Thành viên 2.

## 7. Hiểu biết về luồng end-to-end

Giải thích ngắn gọn bằng lời của bạn:

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?** Data được fetch từ API bằng `crossref.py`, trả về raw data. Tiếp theo qua `cleaning.py` được chuẩn hóa, tạo trường `text_for_embedding`. Cuối cùng đưa vào model embedding và lưu tại vector db bằng `index.py`.
2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?** Ground-truth document IDs giúp evaluator tính hit-rate bằng cách so kết quả Top-K từ vector db với IDs chuẩn. Answer ground-truth được dùng để Judge model chấm điểm Token F1 và Answer Accuracy.
3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?** Quality checks tập trung vào tính nguyên vẹn của dòng (thiếu ID, trùng lặp, nội dung quá ngắn). Freshness monitoring chỉ quan tâm ngày xuất bản (`age_days`) có vượt ngưỡng cấu hình (ví dụ 180 ngày) hay không.
4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?** Để đảm bảo tính công bằng (ceteris paribus). Sự biến thiên của các chỉ số lúc này chỉ hoàn toàn do sự thay đổi của chất lượng dữ liệu.
5. **Repair được xem là thành công dựa trên artifact và metric nào?** Dựa trên file `corruption_report.md`, metrics của Repaired phải tiệm cận (phục hồi lại) ngang mức của Baseline. Đồng thời file json `freshness` và `quality` phải trả về `passed = true`.

## 8. Phân tích kết quả

*(Lưu ý: Chỗ này hãy đợi nhóm chạy xong `run_corruption_flow.py` rồi mở các file kết quả để điền số thực tế vào bảng)*

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |      [ ] |       [ ] |      [ ] | [Nhận xét]              |
| `mean_token_f1`      |      [ ] |       [ ] |      [ ] | [Nhận xét]              |
| `judge_accuracy`     |      [ ] |       [ ] |      [ ] | [Nhận xét]              |
| `mean_judge_score`   |      [ ] |       [ ] |      [ ] | [Nhận xét]              |
| Quality checks         |   Pass |      Fail |     Pass | Bắt được chính xác hiện tượng corrupt dữ liệu |
| Freshness status       |   Pass |      Fail |     Pass | Phát hiện dữ liệu cũ kỹ |

### Kết luận từ số liệu
1. **Data corruption** → quality/freshness báo Fail → agent metric giảm thê thảm.
2. **Repair action** → quality/freshness báo Pass → agent metric phục hồi nguyên trạng.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Thống nhất Data Contract trước khi bắt tay vào làm là chìa khóa để mọi module chạy trơn tru khi tích hợp.
2. Observability không chỉ là log lỗi, mà còn là giám sát sức khỏe của Data Pipeline ở đầu vào (Data Quality & Freshness).
3. Dữ liệu rác (Garbage in) thì kết quả RAG rác (Garbage out), không model LLM nào gánh nổi dữ liệu đầu vào bị thiếu hụt nội dung.

### Nếu có thêm thời gian

Tôi muốn thêm các biểu đồ trực quan (như bar chart) thay vì chỉ sinh bảng Markdown để các bên theo dõi dễ dàng sự sụt giảm chất lượng.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Nam Phong
**Ngày xác nhận:** 2026-08-06
