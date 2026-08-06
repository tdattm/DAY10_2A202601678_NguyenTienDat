# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Lã Phan Hoài An |
| MSSV | 2A202601846 |
| Khóa/Lớp | K4 |
| Tên nhóm | Abe |
| Vai trò chính | Cleaning & Test Set (`cleaning.py`, `testset.py`) |
| Repository | [github.com/tdattm/DAY10_2A202601678_NguyenTienDat](https://github.com/tdattm/DAY10_2A202601678_NguyenTienDat) |
| Commit bàn giao | `f2a279e` — `feat: implement cleaning and evaluation test set` |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Cleaning và data modeling | `src/ingestion/cleaning.py` (`build_clean_dataframe`) | `list[PaperRecord]` từ `crossref.py` và thời điểm chạy | DataFrame theo Clean Schema, dùng để ghi `data/clean/papers_clean.csv` và `data/clean/papers_clean.json` | Hoàn thành |
| Evaluation set | `src/evaluation/testset.py` (`build_test_set`) | Clean DataFrame | `data/eval/test_set.json` gồm câu hỏi, ground truth và document ID | Hoàn thành |

### Việc phối hợp với các module khác

| Hoạt động | Thành viên/module liên quan | Kết quả |
| --- | --- | --- |
| Thống nhất Raw Schema | Thành viên 1 — Source Ingestion | Nhận đúng `PaperRecord` với DOI, title, abstract, authors, subjects, ngày và URL |
| Thống nhất Clean Schema | Thành viên 3, 4 và 5 | Bàn giao đúng 10 cột để observability, corruption và pipeline integration sử dụng |
| Giữ ổn định document identity | Retrieval và Evaluation | Sử dụng DOI làm `paper_id`; loại duplicate không phân biệt hoa/thường |
| Giữ evaluation tái lập | Thành viên 5 — Integration & Comparison | Task 2 ban đầu chọn tối đa 4 paper; khi tích hợp mở rộng thành 6 paper và freeze 17 câu để baseline/corrupted/repaired dùng lại cùng test set |

## 3. Kết quả theo vai trò

### Clean Schema đã bàn giao

| Cột | Ý nghĩa/quy tắc |
| --- | --- |
| `paper_id` | DOI, bắt buộc và unique không phân biệt hoa/thường |
| `title` | Tiêu đề đã chuẩn hóa khoảng trắng, không rỗng |
| `summary` | Abstract/summary đã chuẩn hóa, không rỗng |
| `published` | Ngày chuẩn hóa về `YYYY-MM-DD` |
| `authors_joined` | Danh sách tác giả nối bằng `, ` |
| `categories_joined` | Danh sách category nối bằng `, `; có thể rỗng nếu nguồn không cung cấp |
| `age_days` | Số ngày từ ngày xuất bản đến ngày chạy, không âm |
| `text_for_embedding` | Văn bản tổng hợp title, authors và summary theo phiên bản tích hợp cuối |
| `abs_url` | URL trang DOI/abstract |
| `pdf_url` | URL PDF nếu Crossref cung cấp |

### Artifact và kết quả xác minh thực tế

| Artifact/signal | Kết quả thực tế |
| --- | ---: |
| Raw records nhận từ Task 1 | 24 |
| Clean records | 24 |
| Số cột Clean Schema | 10 |
| DOI trùng lặp | 0 |
| Title null | 0 |
| Summary null | 0 |
| `age_days` âm | 0 |
| Record có authors | 24 |
| Record có categories | 0 |
| Evaluation samples khi kiểm thử Task 2 độc lập | 12 (4 summary, 4 authors, 4 date) |
| Evaluation samples ở pipeline tích hợp cuối | 17 câu `factual` trên 6 DOI |
| Categories questions | 0, vì source không cung cấp category cho corpus hiện tại |

Các artifact đã được tạo và kiểm tra tại:

- `data/clean/papers_clean.csv`
- `data/clean/papers_clean.json`
- `data/eval/test_set.json`

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Raw metadata từ Crossref có thể chứa khoảng trắng dư, danh sách tác giả/category bị trùng, ngày chỉ có năm hoặc năm-tháng, DOI khác nhau về chữ hoa/thường, và một số trường tùy chọn bị thiếu. Phần cleaning cần chuyển dữ liệu này thành schema ổn định cho embedding, retrieval, evaluation, observability và corruption flow.

Evaluation set phải có ground truth bám sát dữ liệu thật, giữ ổn định `paper_id`, đồng thời dùng mẫu câu tương thích với logic exact-title lookup và answer extraction trong `src/retrieval/qa.py`.

### Cách triển khai cleaning

- Khai báo cố định `CLEAN_COLUMNS` gồm đúng 10 cột theo Data Contract.
- Chuẩn hóa chuỗi bằng `normalize_whitespace`.
- Chuẩn hóa authors/categories, loại phần tử rỗng và duplicate không phân biệt hoa/thường nhưng vẫn giữ thứ tự.
- Parse ba dạng ngày Crossref: `YYYY`, `YYYY-MM`, `YYYY-MM-DD` bằng `pandas.to_datetime`.
- Chuẩn hóa ngày về `YYYY-MM-DD` và tính `age_days` theo ngày chạy.
- Loại record thiếu `paper_id`, `title`, `summary`, ngày không hợp lệ hoặc có ngày nằm trong tương lai.
- Loại DOI trùng bằng khóa tạm `paper_id.casefold()`.
- Tạo `text_for_embedding` có cấu trúc ổn định. Phiên bản Task 2 ban đầu chứa title, authors, categories, published và summary; phiên bản tích hợp cuối giữ title, authors và summary.
- Sắp xếp paper mới nhất trước và luôn trả DataFrame đúng thứ tự 10 cột, kể cả khi rỗng.

### Cách triển khai evaluation set

- Kiểm tra DataFrame có đủ các cột bắt buộc và ít nhất 2 paper.
- Phiên bản Task 2 ban đầu chọn tối đa 4 paper mới nhất theo thứ tự xác định, không random, và tạo các dạng `summary`, `authors`, `date`, `categories` khi có ground truth.
- Khi tích hợp, thành viên 5 mở rộng lựa chọn lên 6 paper, chuẩn hóa thành 17 câu `factual` về authors, ngày và vấn đề/ứng dụng, sau đó freeze file để dùng cho cả ba trạng thái.
- Dùng `first_sentence(summary)` cho ground truth dạng summary để khớp cách `qa.py` rút câu trả lời.
- Đặt exact title trong dấu nháy đơn để `qa.py` lookup đúng document.
- Mỗi sample chỉ có đúng 5 trường: `id`, `question_type`, `question`, `ground_truth`, `ground_truth_doc_ids`.
- Ghi JSON bằng utility `write_json`, không hard-code đường dẫn.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input cleaning | `list[PaperRecord]`, `run_date: datetime` |
| Output cleaning | `pd.DataFrame` đúng Clean Schema 10 cột |
| Input test set | Clean DataFrame |
| Output test set | Danh sách JSON sample đúng Evaluation Set Schema |
| Module phụ thuộc | `crossref.py`, `core.utils` |
| Module sử dụng output | `index.py`, `metrics.py`, `quality.py`, `corruption.py`, `phase1.py`, `corruption_flow.py` |

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Crossref có thể trả ngày chỉ gồm năm hoặc năm-tháng, trong khi downstream cần một giá trị ngày thống nhất để tính freshness và tạo ground truth.
- **Các phương án cân nhắc:** Giữ nguyên chuỗi ngày không đồng nhất; loại tất cả ngày thiếu thành phần; hoặc chuẩn hóa bằng `pandas.to_datetime`.
- **Phương án đã chọn:** Parse ngày bằng `pandas.to_datetime(errors="coerce")`, sau đó chuẩn hóa thành `YYYY-MM-DD`.
- **Trade-off:** `2026` được hiểu là `2026-01-01` và `2026-05` là `2026-05-01`. Đây là quy ước chuẩn hóa, không khẳng định ngày đầu tháng/năm là ngày xuất bản chính xác tuyệt đối.
- **Lý do:** Schema thống nhất giúp tính `age_days`, ghi CSV/JSON, lưu Chroma metadata và chấm câu hỏi ngày mà không cần xử lý nhiều định dạng ở các module sau.
- **Bằng chứng:** Dữ liệu thử nghiệm parse được cả ba dạng ngày; corpus thật tạo 24 clean records và không có `age_days` âm.

## 6. Một lỗi hoặc blocker đã xử lý

- **Hiện tượng:** Lần kiểm tra đầu tiên báo `ModuleNotFoundError: No module named 'core'`.
- **Nguyên nhân:** Phiên PowerShell kiểm tra chưa sử dụng Python trong `.venv`, dù project đã được cài editable.
- **Cách xử lý:** Kích hoạt `./.venv/Scripts/Activate.ps1` hoặc gọi trực tiếp `./.venv/Scripts/python.exe`.
- **Kết quả:** Import package thành công; kiểm tra cleaning và test-set bằng dữ liệu giả đều pass.

Một giới hạn dữ liệu khác là toàn bộ 24 records hiện tại có `categories_joined` rỗng do trường `subject` từ Crossref không có dữ liệu. Vì vậy evaluation set không tạo câu hỏi categories để tránh sinh ground truth giả.

## 7. Cách xác minh phần việc

### Kiểm tra schema và chất lượng cleaned data

```powershell
python -c "import pandas as pd; df=pd.read_csv('data/clean/papers_clean.csv'); expected=['paper_id','title','summary','published','authors_joined','categories_joined','age_days','text_for_embedding','abs_url','pdf_url']; print('Schema OK:', df.columns.tolist()==expected); print('Duplicate DOI:', df['paper_id'].str.casefold().duplicated().sum()); print('Null titles:', df['title'].isna().sum()); print('Null summaries:', df['summary'].isna().sum()); print('Negative age_days:', (df['age_days'] < 0).sum())"
```

Kết quả hiện tại sau integration:

```text
Schema OK: True
Duplicate DOI: 0
Null titles: 0
Null summaries: 0
Negative age_days: 0
```

### Kiểm tra evaluation set

```powershell
python -c "import json; d=json.load(open('data/eval/test_set.json', encoding='utf-8')); print('Samples:', len(d)); print({t: sum(x['question_type']==t for x in d) for t in sorted({x['question_type'] for x in d})})"
```

Kết quả đã ghi nhận:

```text
Samples: 17
{'factual': 17}
```

## 8. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?** `crossref.py` fetch và parse API thành `PaperRecord`, sau đó `cleaning.py` chuẩn hóa thành Clean DataFrame và tạo `text_for_embedding`. Phiên bản tích hợp dùng OpenAI `text-embedding-3-small` và lưu vector cùng metadata vào ChromaDB.
2. **Evaluation set và ground-truth document IDs dùng để đo chất lượng ra sao?** Mỗi câu hỏi có câu trả lời chuẩn và danh sách DOI chuẩn. Evaluator kiểm tra retrieved IDs có chứa DOI mong đợi để tính retrieval hit, đồng thời so answer với ground truth để tính token F1 và judge metrics.
3. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?** Dùng cùng câu hỏi và ground truth giữ phép so sánh công bằng; thay đổi metrics khi đó phản ánh thay đổi của corpus thay vì thay đổi đề kiểm tra.
4. **Corruption ảnh hưởng tới phần của tôi thế nào?** Xóa record có thể làm mất ground-truth document, blank/noise summary làm sai context và câu trả lời, stale date ảnh hưởng freshness, còn duplicate phá vỡ uniqueness của `paper_id`.
5. **Repair được xem là thành công khi nào?** Repaired dataset phải khôi phục schema và uniqueness, quality/freshness trở lại trạng thái tốt, và các retrieval/answer metrics tiến gần baseline trên cùng test set.

## 9. Phân tích kết quả

Phần Task 2 được xác minh độc lập trước khi tích hợp, sau đó được kiểm tra lại trên artifact cuối của pipeline. Bảng dưới phân biệt rõ kết quả kiểm thử riêng và kết quả sau khi thành viên 5 tích hợp.

| Metric/signal | Kết quả Task 2 | Nhận xét |
| --- | ---: | --- |
| Raw records | 24 | Nhận từ Source Ingestion |
| Clean records | 24 | Không có record bị loại trong corpus hiện tại |
| Schema validation | Pass | Đúng 10 cột theo contract |
| DOI uniqueness | Pass | 0 duplicate không phân biệt hoa/thường |
| Required text fields | Pass | 0 title/summary null |
| Date validation | Pass | 0 `age_days` âm |
| Evaluation samples độc lập | 12 | 4 summary, 4 authors, 4 date ở thời điểm bàn giao Task 2 |
| Evaluation samples tích hợp | 17 | 17 câu `factual`, 6 ground-truth DOI, dùng chung ba trạng thái |
| Category coverage | 0/24 | Không tạo câu hỏi category vì thiếu ground truth |
| `retrieval_hit_rate` | 1.0000 → 1.0000 → 1.0000 | Baseline → corrupted → repaired |
| `mean_token_f1` | 0.7504 → 0.6905 → 0.7504 | Corruption làm giảm và repair phục hồi đúng baseline |
| `judge_accuracy` | 0.7059 → 0.6471 → 0.7059 | Corruption làm giảm và repair phục hồi đúng baseline |
| `mean_judge_score` | 4.1765 → 3.9412 → 4.2353 | Repair phục hồi và cao hơn baseline 0.0588 |

### Kết luận từ số liệu

Task 2 đã chuyển thành công 24 raw records thành dataset đúng Clean Schema, giữ ổn định DOI và cung cấp nền tảng tạo evaluation set. Sau integration, cùng test set 17 câu cho thấy corruption làm giảm token F1 và judge accuracy, còn repair phục hồi các chỉ số về baseline. Việc không tạo câu hỏi categories là chủ ý đảm bảo trung thực dữ liệu: corpus hiện tại không có category để làm ground truth.

## 10. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Data Contract rõ ràng giúp cleaning, retrieval, observability và corruption tích hợp mà không cần đoán tên hoặc kiểu cột.
2. Ground truth phải xuất phát từ dữ liệu thật; không nên cố tạo đủ loại câu hỏi bằng giá trị giả khi nguồn thiếu metadata.
3. Evaluation set cần ổn định giữa các lần chạy để so sánh baseline, corrupted và repaired có ý nghĩa.

### Nếu có thêm thời gian

- Bổ sung unit tests chính thức cho ngày thiếu thành phần, duplicate DOI, DataFrame rỗng và schema thiếu cột.
- Thiết kế chiến lược chọn paper đại diện theo độ phủ metadata; nếu corpus có category, ưu tiên ít nhất một paper có category.
- Lưu thêm metadata về độ chính xác của ngày để phân biệt ngày đầy đủ với ngày được chuẩn hóa từ năm hoặc năm-tháng.

## 11. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc số liệu để đối chiếu.
- [x] Các kết luận về pipeline tích hợp đã được kiểm chứng bằng artifacts và metrics cuối trên `main`.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc thành viên khác.

**Họ và tên:** Lã Phan Hoài An  
**MSSV:** 2A202601846  
**Ngày xác nhận:** 2026-08-06
