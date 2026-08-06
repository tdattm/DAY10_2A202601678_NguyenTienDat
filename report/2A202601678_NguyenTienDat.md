# Báo cáo vai trò cá nhân — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Nguyễn Tiến Đạt |
| MSSV | 2A202601678 |
| Khóa/Lớp | K4 |
| Tên nhóm | Abe |
| Vai trò chính | Source Ingestion (`crossref.py`) |
| Repository | [github.com/tdattm/DAY10_2A202601678_NguyenTienDat](https://github.com/tdattm/DAY10_2A202601678_NguyenTienDat) |
| Ngày hoàn thành | 2026-08-06 |

## 2. Phạm vi trách nhiệm

### Các hạng mục phụ trách

| Hạng mục | File/hàm chính | Đầu vào | Đầu ra bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Định nghĩa bản ghi nguồn | `src/ingestion/crossref.py` — `PaperRecord` | Metadata không đồng nhất từ Crossref | Data contract gồm 11 trường dùng chung cho pipeline | Hoàn thành |
| Phân tích phản hồi API | `parse_crossref_payload` | JSON trả về từ endpoint `/works` | Danh sách `PaperRecord` hợp lệ | Hoàn thành |
| Thu thập và lưu dữ liệu | `fetch_source_records` | `Settings`: query, filter, số lượng record | Raw response và raw records trong `data/raw/` | Hoàn thành |
| Tái sử dụng snapshot | `load_raw_records` | `crossref_records.json` | Danh sách object `PaperRecord` cho baseline/repair | Hoàn thành |

### Phối hợp với các phần khác

- Bàn giao `PaperRecord` cho module cleaning; DOI được dùng làm `paper_id` xuyên suốt cleaning, embedding và evaluation.
- Cung cấp snapshot bất biến `data/raw/crossref_records.json` để corruption flow phục hồi dữ liệu, thay vì sửa trực tiếp trên dataset đã bị làm hỏng.
- Thống nhất các trường văn bản, ngày xuất bản và URL để thành viên tích hợp có thể chạy pipeline mà không cần biết cấu trúc JSON gốc của Crossref.

## 3. Kết quả bàn giao và bằng chứng

Implementation Source Ingestion được đưa vào repository từ commit `0246a84` với nội dung `feat(ingestion): implement Crossref data ingestion`. Phiên bản hiện tại đã được dùng bởi cả Phase 1 và luồng repair.

| Bằng chứng | Kết quả quan sát được |
| --- | ---: |
| Số item trong Crossref response | 24 |
| Số raw record parse thành công | 24 |
| Số `paper_id` duy nhất | 24 |
| Record có summary | 24/24 |
| Record có tác giả | 24/24 |
| Record có ngày xuất bản | 24/24 |
| Record có category từ nguồn | 0/24 |
| Record còn lại sau cleaning | 24 |

Các artifact nguồn đã được sinh:

- `data/raw/crossref_response.json`: phản hồi nguyên bản từ Crossref, phục vụ truy vết.
- `data/raw/crossref_records.json`: danh sách record đã parse theo data contract.
- `data/clean/papers_clean_repaired.json`: bằng chứng corruption flow có thể dựng lại dữ liệu sạch từ snapshot nguồn.

Tại thời điểm rà soát, repository không còn `TODO(student)` hoặc `NotImplementedError` trong `src/`; kiểm tra compile cho `src/` và `script/` thành công. Baseline, corrupted và repaired đều đã có dataset, embedding manifest, answers, metrics và báo cáo. Repository hiện chưa có test suite tự động riêng.

## 4. Mô tả kỹ thuật phần Source Ingestion

### Cấu hình truy vấn

Pipeline sử dụng Crossref REST API với endpoint `/works` và các tham số sau:

| Thuộc tính | Giá trị thực tế |
| --- | --- |
| Query parameter | `query.bibliographic` |
| Query | `agentic retrieval augmented generation large language model` |
| Filter tại lần rà soát | `from-pub-date:2026-02-07,has-abstract:true` |
| Số kết quả yêu cầu | 24 |
| Timeout mỗi request | 30 giây |
| HTTP status được retry | 429, 500, 502, 503, 504 |
| Số lần thử tối đa | 4 |

Khi gặp lỗi tạm thời, hàm ưu tiên giá trị `Retry-After` từ server; nếu header không có hoặc không hợp lệ thì dùng exponential backoff. Khoảng chờ được giới hạn tối đa 30 giây.

### Quy tắc parse và chuẩn hóa

`parse_crossref_payload` duyệt qua `message.items` và xử lý từng item độc lập:

1. Lấy DOI làm định danh ổn định và lấy title đầu tiên có nội dung.
2. Ưu tiên `abstract`, sau đó dùng `description` làm fallback cho summary.
3. Loại record thiếu DOI, title hoặc summary để tránh đưa tài liệu không đủ nội dung vào bước embedding.
4. Ghép `given` và `family` thành tên tác giả; lấy `subject` làm categories khi nguồn cung cấp.
5. Chọn ngày theo thứ tự ưu tiên và hỗ trợ cả định dạng chỉ có năm, năm-tháng hoặc đầy đủ ngày.
6. Tìm URL PDF từ danh sách `link`; nếu thiếu URL trang abstract thì dựng URL DOI làm fallback.
7. Gỡ thẻ HTML/JATS và chuẩn hóa khoảng trắng trong abstract.

Data contract đầu ra gồm:

| Trường | Ý nghĩa |
| --- | --- |
| `paper_id` | DOI, dùng làm định danh tài liệu |
| `title` | Tiêu đề đã chuẩn hóa |
| `summary` | Abstract/description đã loại markup |
| `authors` | Danh sách tên tác giả |
| `categories`, `primary_category` | Chủ đề do Crossref cung cấp |
| `published`, `updated` | Ngày xuất bản và cập nhật tốt nhất tìm được |
| `abs_url`, `pdf_url` | URL DOI/trang bài báo và PDF nếu có |
| `comment` | Ghi chú bổ sung từ nguồn |

### Khả năng truy vết và tái lập

Tôi lưu hai lớp artifact thay vì chỉ giữ kết quả cuối. Raw response giúp kiểm tra lại chính xác dữ liệu nhà cung cấp đã trả về, còn parsed records ổn định hóa schema cho các module phía sau. Khi `REFRESH_SOURCE` không bật và snapshot đã tồn tại, Phase 1 có thể đọc lại dữ liệu cục bộ; cách này giảm phụ thuộc mạng và tránh kết quả thay đổi giữa các lần chạy. Cùng snapshot đó được dùng làm nguồn tin cậy cho bước repair.

## 5. Quyết định kỹ thuật quan trọng

Quyết định quan trọng nhất là sử dụng DOI làm `paper_id` và duy trì raw snapshot riêng biệt.

- Nếu dùng số thứ tự của item trong response, định danh có thể đổi khi Crossref thay đổi thứ tự kết quả.
- DOI có ý nghĩa ở cấp tài liệu, giúp đối chiếu ground truth với kết quả retrieval và phát hiện duplicate.
- Snapshot raw không bị ghi đè bởi corruption trên clean dataset, nên repair có thể quay lại dữ liệu trước biến đổi.

Kết quả thực tế cho thấy lựa chọn này hoạt động đúng: baseline có 24 DOI duy nhất; corruption tạo một duplicate và quality check phát hiện được; repair từ raw snapshot đưa số duplicate trở lại 0.

## 6. Vấn đề gặp phải và giới hạn hiện tại

Crossref không đảm bảo mọi publication có cùng mức độ đầy đủ. Abstract có thể chứa JATS/HTML, ngày có thể chỉ có năm hoặc tháng, và một số trường như subject/PDF URL không bắt buộc. Code hiện tại xử lý markup, partial date và trường tùy chọn mà không làm hỏng toàn bộ batch.

Trong snapshot thực tế, cả 24 record đều không có category. Tôi giữ `categories` là danh sách rỗng thay vì tự suy diễn chủ đề, vì tự gán nhãn không có căn cứ sẽ làm sai nguồn dữ liệu. Hạn chế này làm phần category không đóng góp vào `text_for_embedding`, nhưng title, summary, authors và published vẫn đầy đủ.

Hai điểm có thể cải thiện thêm:

- Retry hiện xử lý HTTP status tạm thời nhưng chưa bắt riêng các exception mạng như connection timeout/reset.
- `User-Agent` vẫn dùng địa chỉ email minh họa; khi vận hành thật nên cấu hình contact hợp lệ theo khuyến nghị của Crossref.

## 7. Hiểu biết về luồng end-to-end

1. **Từ API đến vector store:** Crossref response được lưu nguyên bản, parse thành `PaperRecord`, làm sạch thành DataFrame và tạo `text_for_embedding`. MiniLM sinh vector, sau đó ChromaDB lưu vector cùng DOI và metadata.
2. **Vai trò của DOI trong evaluation:** `ground_truth_doc_ids` chứa DOI của tài liệu đúng. Evaluator so các DOI này với danh sách tài liệu retrieval trả về để tính `retrieval_hit_rate`.
3. **Vì sao phải giữ test set cố định:** Baseline, corrupted và repaired chỉ có thể so sánh công bằng khi cùng trả lời một tập câu hỏi và cùng ground truth.
4. **Corruption ảnh hưởng dữ liệu nguồn ra sao:** Luồng corruption chỉ thay đổi derived clean data; raw response và parsed snapshot không bị sửa.
5. **Repair hoạt động như thế nào:** Pipeline đọc lại 24 `PaperRecord` từ `crossref_records.json`, chạy lại cleaning, rebuild index rồi đánh giá trên test set cũ.

## 8. Phân tích kết quả toàn pipeline từ góc nhìn ingestion

### Evaluation metrics

| Metric | Baseline | Corrupted | Repaired | Nhận xét |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.0000 | 1.0000 | 1.0000 | Corruption chưa làm mất ground-truth document khỏi top-k |
| `mean_token_f1` | 0.7504 | 0.6905 | 0.7504 | Nội dung lỗi làm chất lượng câu trả lời giảm; repair phục hồi đúng mức baseline |
| `judge_accuracy` | 0.7059 | 0.6471 | 0.7059 | Accuracy giảm khi dùng corrupted corpus và phục hồi sau repair |
| `mean_judge_score` | 4.1765 | 3.9412 | 4.2353 | Repaired cao hơn nhẹ baseline; có thể có dao động từ bước judge |

Ragas chưa được chạy vì artifact ghi nhận `RUN_RAGAS` chưa được bật.

### Data quality và freshness

| Signal | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
| Số dòng | 24 | 25 | 24 |
| Duplicate DOI | 0 | 1 | 0 |
| Summary quá ngắn/rỗng | 0 | 1 | 0 |
| Dòng stale | 0 | 1 | 0 |
| Quality tổng thể | Pass | Fail | Pass |
| Freshness | Pass | Fail | Pass |

Các số liệu cho thấy raw snapshot hoàn thành đúng vai trò recovery point: sau khi clean data bị thêm duplicate, xóa summary và đổi ngày về năm 2000, việc dựng lại từ raw records khôi phục số dòng, quality/freshness và các metric answer về gần hoặc bằng baseline. `retrieval_hit_rate` không đổi nên không thể kết luận corruption làm retrieval kém trong lần chạy này; ảnh hưởng rõ nhất nằm ở Token F1 và kết quả judge.

## 9. Điều rút ra và hướng cải thiện

### Những điều học được

1. Ingestion không chỉ là gọi API; việc lưu raw artifact quyết định khả năng audit và phục hồi của toàn pipeline.
2. Một định danh bền vững như DOI giúp nối dữ liệu qua nhiều pha và làm cho phép đo retrieval có thể kiểm chứng.
3. Schema nguồn bên ngoài luôn có trường tùy chọn, vì vậy parser phải chấp nhận thiếu dữ liệu có kiểm soát nhưng vẫn loại record không đủ điều kiện cho use case RAG.

### Nếu tiếp tục hoàn thiện

Tôi sẽ bổ sung unit test cho payload thiếu `message/items`, abstract chứa JATS, partial date, malformed author/link và retry khi phát sinh exception mạng. Ngoài ra, tôi sẽ đưa endpoint và contact trong `User-Agent` vào cấu hình để module ingestion phù hợp hơn với môi trường vận hành thật.

## 10. Tự xác nhận

- [x] Báo cáo mô tả đúng phạm vi Source Ingestion mà tôi phụ trách.
- [x] Các con số được đối chiếu với artifact hiện có trong repository.
- [x] Tôi phân biệt rõ kết quả thực tế, hạn chế dữ liệu và đề xuất cải thiện.
- [x] Tôi hiểu cách output của `crossref.py` được cleaning, retrieval, evaluation và repair sử dụng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Nội dung được viết riêng cho vai trò Source Ingestion, không sao chép báo cáo của thành viên khác.

**Họ và tên:** Nguyễn Tiến Đạt  
**Ngày xác nhận:** 2026-08-06
