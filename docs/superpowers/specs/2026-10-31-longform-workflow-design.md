# Thiết kế: workflow video dài lịch sử, đa ngôn ngữ

Soạn 2026-10-31 từ buổi trao đổi với chủ kênh. Tài liệu viết bằng tiếng Việt cho chủ kênh duyệt; tên file, lệnh, code giữ tiếng Anh.
Những chỗ ghi **[Claude quyết]** là lựa chọn của Claude, chủ kênh chưa nói; chủ kênh có thể đổi.

## 1. Mục đích và lý do

Chủ kênh dừng mọi kênh khác và bỏ hẳn Short để tập trung vào **một loại sản phẩm: video lịch sử dài 10–15 phút, hoạt hình 2D đơn giản, xuất nhiều ngôn ngữ từ cùng một bộ hình**. Mỗi ngôn ngữ lên một kênh YouTube riêng, nhưng việc đó nằm ngoài workflow: workflow chỉ biết "dự án video" và "ngôn ngữ", không biết "kênh".

Lý do chọn hướng này:
- Đề tài lịch sử Việt Nam có nhu cầu lớn cả trong và ngoài nước (đo ngày 2026-10-31: "how vietnam defeated the mongols" trung vị ~747 nghìn view; bản tiếng Việt ~3,3 triệu; nhiều kênh nhỏ dưới 100 nghìn sub vẫn đạt vài trăm nghìn view; file `channels/vn-history/research/scout/longform_first_20261031.csv`).
- Một bộ hình dùng cho 5 ngôn ngữ thì chi phí mỗi ngôn ngữ thêm rất thấp.
- Video mẫu chủ kênh chọn ("How Rome Conquered Greece", kênh Ancient Romans, 3 nghìn sub, 231 nghìn view, 25 phút) chỉ là ảnh tĩnh AI, chữ trong ảnh sai, bản đồ méo, nhân vật đổi mặt giữa cảnh. Workflow này phải làm tốt hơn ở đúng các điểm đó: có chuyển động, nhân vật giữ nguyên, chữ và bản đồ đúng, đổi được ngôn ngữ.

Thành công nghĩa là: chủ kênh làm được một video 10–15 phút từ đề tài đến 5 file MP4 (VI, EN, JA, DE, ES) mà việc của chủ kênh chủ yếu là **chat yêu cầu, duyệt và quyết định**, không phải sửa tay từng file; và không câu nào trong video nói sai sự thật mà không bị hệ thống chặn hoặc đánh dấu.

## 2. Mục tiêu, không làm, chống mục tiêu

**Mục tiêu**
1. Một workflow duy nhất cho video dài, một dashboard riêng cho nó.
2. Bước kịch bản dạng chat với AI, có ngân hàng dữ kiện chặn thông tin không nguồn.
3. AI chỉ vẽ nền, ngoại cảnh, đạo cụ và bộ ảnh nhân vật quan trọng; Remotion làm toàn bộ chuyển động, chữ, bản đồ.
4. Nhân vật quan trọng giữ đúng một "format" ở mọi cảnh, mọi video.
5. Xuất nhiều ngôn ngữ từ cùng một bộ cảnh; danh sách ngôn ngữ chọn được, bộ đầu: vi, en, ja, de, es.
6. Review ảnh chạy song song, ảnh nào xong chấm ngay; mọi việc cần chủ kênh gom về một chỗ.

**Không làm (lúc này)**
- Short, video dọc, Veo, gflow/Google Flow (cả cho ảnh), bìa 9:16. Bỏ hẳn.
- Quản lý kênh YouTube trong workflow (brand, handle, nhiều kênh).
- Animation nói (khớp môi), rối có khớp tay chân kiểu cutout rig.
- Upload tự động lên YouTube (API chưa audit sẽ khóa video ở private); chủ kênh vẫn tự upload.
- n8n, chạy trên máy Windows: đã bàn, để sau. Không cần làm code chạy được trên Windows trong đợt này, nhưng không thêm phụ thuộc macOS mới.
- Văn phòng 3D (`/office`): bỏ.

**Chống mục tiêu (dù chạy được vẫn là thất bại)**
- Kịch bản có một câu nêu sự kiện, số, tên, ngày mà không truy được về nguồn có trích nguyên văn.
- Nhân vật quan trọng trông khác nhau giữa các cảnh.
- Chữ nằm trong ảnh AI (không đổi được ngôn ngữ, dễ sai chính tả).
- Văn phong hàn lâm, đọc như bài giảng.
- Chủ kênh phải ngồi chờ: review chạy tuần tự, một bước chậm chặn cả dây chuyền, hoặc phải tự đi tìm xem việc gì đang chờ mình.

## 3. Ràng buộc (giữ từ trước)

- Xuất 1440p (2560x1440, ~16 Mbps H.264, AAC 48 kHz), chỉ giữ file cuối.
- Không bịa số, người, nguyên nhân. Mọi con số đọc lên có dòng nguồn.
- Lời đọc không đọc tên nguồn hiện đại (tác giả, bài báo, bảo tàng, URL). Mô tả YouTube có một dòng nguồn ngắn, chỉ tên, không link. Ngoại lệ: khi các ghi chép lịch sử vênh nhau, lời đọc nêu cả hai bằng từ thường ("sử nhà Trần chép…, còn sử nhà Nguyên lại ghi…").
- Không thêm dòng "Video minh họa bằng AI…" vào mô tả; dùng cài đặt nội dung tổng hợp (altered/synthetic = Yes) khi upload.
- Bản quyền: giọng ElevenLabs phải từ gói trả phí khi kiếm tiền; nhạc phải có giấy phép cho YouTube kiếm tiền; font giấy phép mở (OFL); không dùng ảnh/clip của bên thứ ba (kể cả làm tham chiếu cho AI); Remotion miễn phí cho cá nhân hoặc công ty ≤3 người (`LICENSES.md`).
- Luật review: Gemini chấm 1–5. 4–5 qua; 3 chờ chủ kênh duyệt; 1–2 tự làm lại với lời sửa của review, tối đa 2 lần, sau đó chờ chủ kênh. Ảnh có thứ trong danh sách MUST NOT bị chấm tối đa 3.
- Prompt ảnh viết theo spec có cấu trúc, không từ mơ hồ ("some", "a few", "dramatic", "cinematic"…), kích thước so với cơ thể hoặc đồ vật thay vì mm/cm. Mỗi prompt kèm khối MUST từ bài học của kênh (`prompt_lessons.json`) và lời sửa pre-flight của Gemini.
- Hàng đợi ghi trên đĩa; tạm dừng thì hoàn tất bước đang chạy, không bắt đầu bước mới; không bước nào (review, rút bài học) được chặn bước khác.
- Telegram báo việc cần chủ kênh và việc hỏng (`tools/notify.py`).
- Chạy trên Mac của chủ kênh, dashboard chỉ nghe `127.0.0.1`.

## 4. Những gì chủ kênh đã quyết

### 4.1 Dọn workspace

Đã làm ngày 2026-10-31 (chuyển, không xóa) sang `/Users/quoctung/Documents/AI/archive/2026-10-31/`: kênh fossil-receipts, median-worker, horror-tales và 4 video Short của kênh lịch sử (test-001, 002, 003, 004). Các `research/sources_log.csv` trong đó vẫn dùng làm nguồn được.

Còn phải gỡ khỏi workspace (chuyển vào archive, không xóa): `tools/shorts/`, các nhánh `is_shorts` và nút Short trong dashboard, `dashboard/office/`, `dashboard/vendor/three/`, route `/office`, mục 12 của `HANDOFF.md`, các phần Short trong `CLAUDE.md`, và code chỉ phục vụ Short hoặc kênh cũ. **[Claude quyết]** Các skill `yt-*` trong `/Users/quoctung/Documents/AI/.claude/skills/` viết cho The Median Worker: chuyển vào archive; phần còn dùng được (cấu trúc giữ chân người xem, kiểm hook) chép vào hướng dẫn mới của workflow. `CLAUDE.md` và `HANDOFF.md` viết lại cho workflow mới.

Giữ lại và đưa vào workflow mới: bài học viết prompt và cơ chế MUST block (`prompt_lessons.json`, `tools/gemini/lessons.py`, `preflight.py`), luật review, phần kiểm chứng nguồn trong `channels/vn-history/LESSONS.md`.

### 4.2 Video xoay quanh dự án, không xoay quanh kênh

- Thư mục `channels/` bỏ. Brand hiện có của Công Trường Lịch Sử (avatar, banner, watermark) để riêng ngoài workflow.
- **[Claude quyết]** Bố cục:
  - `projects/NNN-slug/`: phần dùng chung của một video: research, ngân hàng dữ kiện, kịch bản gốc tiếng Việt, cảnh Remotion, ảnh nền và đạo cụ của video.
  - `projects/NNN-slug/lang/<mã>/`: phần riêng mỗi ngôn ngữ: kịch bản dịch, giọng, timing, phụ đề, thumbnail, text upload, file render.
  - `library/`: dùng chung mọi video: bộ nhân vật quan trọng, kiểu đám đông, nền dùng lại được, sổ văn phong, bảng thuật ngữ và phiên âm theo ngôn ngữ, bài học prompt.
  - `config/languages.json` (hoặc tương đương): mỗi ngôn ngữ có engine giọng, giọng, tốc độ, font, quy tắc ngắt dòng. Mỗi dự án chỉ chọn danh sách ngôn ngữ cần xuất.
- Độ dài mục tiêu 10–15 phút. Tiếng Việt là ngôn ngữ gốc.

### 4.3 Các bước

1. **Đề tài** (đo nhu cầu bằng `tools/research/scout.py`, như hiện có).
2. **Nghiên cứu + kịch bản** qua chat (mục 4.4).
3. **Hình ảnh**: nền, đạo cụ, ảnh nhân vật quan trọng còn thiếu (mục 4.5).
4. **Cảnh**: mỗi câu gắn nền, nhân vật, chuyển động; xem trước bằng Remotion (mục 4.6).
5. **Ngôn ngữ**: dịch, kiểm, giọng cho từng ngôn ngữ (mục 4.7).
6. **Render**: một MP4 1440p cho mỗi ngôn ngữ, cùng phụ đề `.srt` và chương.
7. **Upload texts + thumbnail** cho mỗi ngôn ngữ; chủ kênh tự upload.

Các bước 3–5 chạy chồng lên nhau được: dịch và làm giọng không cần đợi xong hình; cảnh không cần đợi xong mọi ngôn ngữ.

### 4.4 Bước kịch bản: chat + ngân hàng dữ kiện

Giao diện 3 cột (bản phác: `.superpowers/brainstorm/34991-1793441859/content/script-chat.html`):
- **Chat**: chủ kênh gõ yêu cầu tự do: tìm tư liệu, đề xuất dàn ý, viết đoạn, sửa giọng văn, kiểm lại một câu.
- **Ngân hàng dữ kiện**: mỗi dữ kiện là một khẳng định ngắn, kèm URL, đoạn trích nguyên văn, bản lưu nội dung trang, hạng nguồn, trạng thái (✅ đã kiểm / ⚠️ nguồn yếu / ⛔ mâu thuẫn / ⏳ đang kiểm) và người kiểm.
- **Kịch bản**: mỗi câu gắn mã dữ kiện nó dùng. Câu nêu sự kiện, số, tên, ngày mà không có dữ kiện ✅ hiện đỏ; câu dùng dữ kiện ⚠️ hiện vàng (chủ kênh quyết). Nút "Chốt kịch bản" chỉ bật khi không còn câu đỏ.

Luật chống bịa (chạy tự động sau mỗi lượt AI):
1. AI viết chỉ được dùng dữ kiện đã có trong ngân hàng. Văn thì viết lại tự do; dữ kiện mới phải vào ngân hàng và qua kiểm trước khi được dùng.
2. Không có trích nguyên văn thì không phải dữ kiện.
3. Hạng nguồn: A = bài khoa học, bảo tàng, cơ quan di sản, bản dịch chính sử đã xuất bản; B = báo lớn, bách khoa; C = blog, trang du lịch, wiki. Con số cần 1 nguồn A hoặc 2 nguồn B độc lập; nguồn C không đủ một mình.
4. Kiểm độc lập: một model khác với model viết. **Chia việc (chủ kênh, 2026-10-31):** agy (Gemini) tìm nguồn và viết bản kịch bản đầu; Claude review lại kịch bản: đối chiếu từng dữ kiện với nguồn, nội dung và văn phong tự mở lại nguồn và trả lời "nguồn có nói đúng điều này không".
5. Mức chắc chắn phải hiện trong lời: "tương truyền" cho truyền thuyết, "có ý kiến cho rằng" cho chỗ tranh cãi, "cho thấy" chứ không "chứng minh" cho khảo cổ.
6. Khi các ghi chép vênh nhau: nêu cả hai, nói rõ bên nào ghi gì, bằng giọng kể chuyện (biến chỗ vênh thành câu hỏi mở, một ý một câu, số tròn khi đọc, số chính xác hiện trên thẻ hai cột trên màn hình). Không tự giải thích vì sao khác, trừ khi có nguồn. **[Claude quyết]** Mỗi video chỉ đưa 1–3 chỗ vênh quan trọng nhất; chỗ vênh không cần cho câu chuyện thì bỏ dữ kiện đó.

**Claude chạy trên gói Claude hiện tại** (Claude Code headless, như ô Claude trên dashboard), không dùng API key (chủ kênh chọn 2026-10-31). Phần việc nặng (tìm nguồn, viết nháp, toàn bộ hình ảnh) do agy (gói Ultra) làm; Claude làm review kịch bản và Remotion; khi chạm giới hạn quota, việc Claude dừng ở trạng thái lưu được và tiếp tục sau, không mất phần đã làm.

Chủ kênh hiểu hệ thống này giảm mạnh rủi ro sai nhưng không bảo đảm 100%; chủ kênh là người chốt ở câu vàng và đỏ.

**Văn phong**: giọng **người kể chuyện lịch sử** (không phải giọng "Hôm nay, bạn sẽ xây…" của Short), thỉnh thoảng hỏi thẳng người xem. Giữ từ các Short đã làm và các lần chủ kênh sửa: hài nhẹ, dễ hiểu cho khán giả trẻ; câu ngắn; mỗi đoạn có thể chốt bằng một câu đùa gọn; tiếng lóng Việt nhẹ, không lóng tiếng Anh (TTS đọc sai); hook bằng câu hỏi thật, không mở bằng "chúc mừng"; khi gọi người xem dùng "bạn", không "chúng ta", không "bạn nhỏ"; đùa không bẻ sự thật; kết bằng twist khảo cổ hoặc "ngày nay còn lại gì"; số đọc dễ nghe. Bốn kịch bản Short trong archive là ví dụ giọng văn.

**Sổ văn phong tự học**: mỗi lần chủ kênh bảo sửa giọng văn trong chat, AI đề xuất một quy tắc rút ra; chủ kênh bấm giữ hoặc bỏ; quy tắc giữ lại dùng cho mọi video sau. Mỗi ngôn ngữ có sổ riêng.

Kịch bản video dài cần mạch chương (ví dụ cho đề tài Mông–Nguyên: hook so sánh với Nhật → sức mạnh Mông Cổ → hai lần đầu → 1288 và Bạch Đằng → cách làm bãi cọc và tính con nước → trận đánh → bằng chứng khảo cổ → kết), mỗi 60–90 giây mở một câu hỏi mới để giữ người xem.

### 4.5 Hình ảnh

**Chia việc**: agy đảm nhận **toàn bộ phần hình ảnh** (tạo và review; chủ kênh bỏ hẳn gflow/Flow ngày 2026-10-31) vẽ **nền, ngoại cảnh, đạo cụ và bộ ảnh nhân vật quan trọng**. Mọi chuyển động, chữ, bản đồ, nhãn là việc của Remotion.

**Style**: theo video mẫu: nét mực đen kiểu truyện tranh châu Âu, màu phẳng nhạt như màu nước, nền chi tiết hơn nhân vật, góc nhìn ngang tầm mắt. Mẫu animation chủ kênh đưa: `/Users/quoctung/Downloads/march.mp4` (nền AI không người; đoàn lính người que vẽ bằng code đi theo đường cong, nhỏ dần theo chiều sâu; tiêu đề và ngày bằng chữ Remotion; camera mở từ màn đen rồi zoom, lia chậm).

**Chất lượng ảnh** (chủ kênh, 2026-10-31: phải đạt chất lượng video YouTube): công cụ tạo ảnh của agy không có tùy chọn độ phân giải và trả ảnh khoảng 1376x768, nên mọi ảnh qua một bước **phóng to bằng AI chạy trên máy** trước khi dùng, sao cho nền đạt tối thiểu 2560x1440 thật (cộng dư cho camera zoom) và nét mực không nhòe; ảnh không đạt thì bị loại ở bước kiểm máy.

**Nền**: không người, không chữ, có đường mặt đất hoặc con đường để nhân vật đứng/đi, rộng hơn khung 16:9 để camera lia. Review đánh trượt nền có người hoặc chữ. Nền dùng lại được thì vào `library/`.

**Nhân vật chia 2 hạng**:
- **Đám đông** (lính, dân, phu thuyền…): người que đơn giản, Remotion vẽ hoàn toàn bằng code như mẫu `march.mp4`: đầu tròn to, mắt to, tay chân que, mũ và vũ khí theo phe. Phe phân biệt bằng dáng mũ, màu áo, vũ khí. Không tốn ảnh AI.
- **Nhân vật quan trọng**: vẽ đầy đủ áo quần, đúng style nền, **tỉ lệ cartoon đầu to (~4 đầu), mặt đơn giản** như nhân vật trong video mẫu (chủ kênh chọn 2026-10-31), để đứng cạnh đám đông người que vẫn cùng một thế giới. Style `vn-ligne-claire` của Short (người ~6 đầu, cấm đầu to) không dùng; cần một style lock mới cho video dài (nền + nhân vật), xác định qua thử nghiệm sớm. **[Claude quyết]** AI vẽ thành **bộ ảnh rời** (các tư thế toàn thân, các biểu cảm), nền trong suốt; Remotion chỉ ghép và diễn. **[Claude quyết]** Ranh giới hai hạng: nhân vật có tên và xuất hiện từ 2 cảnh trở lên là nhân vật quan trọng.

**Giữ đúng format nhân vật quan trọng**:
- Mỗi nhân vật có một bộ được duyệt một lần, lưu trong `library/` (dùng lại cho mọi video), gồm: model sheet gốc, danh sách tư thế, danh sách biểu cảm, chiều cao chuẩn, điểm neo chân, màu trang phục.
- Mỗi kịch bản có một ảnh tổng gồm mọi nhân vật quan trọng với mọi tư thế dùng trong video, ghép từ ảnh đã duyệt (không cho AI tạo ảnh tổng), dùng làm tham chiếu cho các lần tạo sau.
- Cảnh Remotion chỉ được gọi nhân vật qua component của bộ (dạng `<Hero id pose expr>`); công cụ kiểm tra từ chối ảnh nhân vật lẻ, tư thế/biểu cảm không có trong bộ, hoặc tự đổi tỉ lệ ngoài quy tắc.
- AI không bao giờ vẽ nhân vật quan trọng vào nền.
- Cần tư thế mới: AI sửa từ ảnh gốc đã duyệt → Gemini so với bộ → chủ kênh duyệt → thêm vào bộ.

### 4.6 Animation (Remotion)

Đơn giản, không nói:
- Nhân vật quan trọng: thở nhẹ, chớp mắt (nếu bộ có ảnh mắt nhắm), đổi tư thế/biểu cảm theo câu, trượt vào/ra khung, bóng dưới chân.
- Đám đông: bước chân, nhún đầu, đi theo đường, tự xếp hàng, nhỏ dần theo chiều sâu, biểu cảm ngẫu nhiên.
- Camera: zoom, lia trên nền; mở/chuyển cảnh mềm.
- Chữ: tiêu đề chương, ngày, nhãn tên, thẻ so sánh hai nguồn, chữ chạy, tất cả theo ngôn ngữ đang render.
- Bản đồ: Remotion vẽ từ đường bờ biển thật (Natural Earth, public domain) với lớp tô kiểu vẽ tay; mũi tên hành quân chạy; biên giới lịch sử phải có nguồn trong ngân hàng dữ kiện. Không dùng bản đồ do AI vẽ.

Phần Remotion cần AI (viết cảnh, ghép phân cảnh, chỉnh chuyển động) do **Claude** làm (chủ kênh, 2026-10-31). Cảnh gắn theo **mã cảnh (beat)**, không theo số câu, nên cùng một file cảnh dùng cho mọi ngôn ngữ; thời lượng mỗi cảnh tự theo giọng của ngôn ngữ đang render.

### 4.7 Đa ngôn ngữ

- Danh sách ngôn ngữ chọn được theo dự án; bộ đầu: vi (gốc), en, ja, de, es; thêm ngôn ngữ chỉ cần khai báo.
- **Không dịch, mà viết lại kịch bản bằng từng ngôn ngữ** (chủ kênh, 2026-10-31), để văn phong tự nhiên với khán giả nước đó. agy viết bản mỗi ngôn ngữ từ **ngân hàng dữ kiện + dàn ý theo cảnh** (không dịch từ câu tiếng Việt), dùng một skill viết lại/bản địa hóa riêng cho agy, sổ văn phong và bảng thuật ngữ của ngôn ngữ đó; Claude review như bản tiếng Việt (dữ kiện, nội dung, văn phong).
- **Đơn vị khớp hình là cảnh (beat), không phải câu** [Claude quyết, hệ quả của việc viết lại]: mỗi cảnh có danh sách dữ kiện và hình cố định; bản mỗi ngôn ngữ viết lại cảnh đó bằng số câu tùy ý nhưng chỉ dùng đúng các dữ kiện của cảnh; thời lượng cảnh theo giọng của ngôn ngữ đó.
- Kiểm tự động mỗi bản ngôn ngữ: đủ cảnh, mỗi cảnh không có dữ kiện ngoài danh sách của nó, đủ con số, tên riêng khớp bảng thuật ngữ.
- `library/` có bảng thuật ngữ lịch sử và bảng phiên âm tên riêng cho từng ngôn ngữ (ví dụ Trần Hưng Đạo trong tiếng Nhật: チャン・フン・ダオ), dùng chung mọi video.
- Giọng: tiếng Việt Vbee (tốc độ đã đo 1.13); en/ja/de/es ElevenLabs đa ngôn ngữ (gói trả phí). Cấu hình giọng, tốc độ theo ngôn ngữ.
- **Chủ kênh tự tạo giọng trên web** (chọn 2026-10-31), không qua API. Workflow chuẩn bị sẵn text từng phần theo giới hạn của mỗi công cụ (Vbee chèn câu hệ thống khi một file dài hơn ~1 phút, nên cắt dưới mức đó; ElevenLabs dùng extension Edge `tools/edge-tts-batch` như hiện có), đặt tên file sẵn, hiện thành việc trong "Cần bạn" cho từng ngôn ngữ; chủ kênh kéo thả mp3 vào là workflow tự nhận, tự kiểm đủ phần, tự dò thời điểm từng câu bằng khoảng lặng như hiện có.
- Font: font chữ Việt hiện có (Be Vietnam Pro) cộng một font tiếng Nhật giấy phép OFL (ví dụ Noto Sans JP); chữ Nhật cần quy tắc ngắt dòng riêng.
- Mỗi ngôn ngữ có thumbnail (chữ do code vẽ), title, mô tả, tag, phụ đề, chương, file render riêng.

### 4.8 Nhạc nền và hiệu ứng âm thanh

Chủ kênh chọn (2026-10-31) **nhạc nền + hiệu ứng âm thanh nhẹ**, để video không chỉ có giọng đọc từ đầu đến cuối và không nhàm.
- Nhạc nền theo chương (mở đầu, căng thẳng, trận đánh, kết), lấy từ thư viện nhạc có giấy phép cho YouTube kiếm tiền do chủ kênh cung cấp nguồn; nhạc tự hạ khi có giọng.
- Hiệu ứng âm thanh rải theo cảnh, nhẹ, dưới giọng: đao kiếm chạm nhau, tiếng trống trận, sóng nước, mái chèo, bước chân đoàn quân, tiếng búa đóng cọc, gió… Bảng cảnh có thêm cột âm thanh; **[Claude quyết]** AI đề xuất hiệu ứng theo nội dung từng câu, chủ kênh sửa hoặc bỏ.
- Âm thanh không phụ thuộc ngôn ngữ, dùng chung cho mọi bản; vị trí bám theo câu nên tự khớp với thời lượng từng ngôn ngữ.
- Mọi file nhạc và hiệu ứng phải có giấy phép cho phép kiếm tiền, ghi vào `LICENSES.md`.

### 4.9 Review và duyệt

- Ảnh nào tạo xong được chấm ngay (dây chuyền), không đợi cả đợt; ảnh trượt làm lại ngay theo luật mục 3.
- Số luồng chạy song song chỉnh được trên dashboard, có trần theo quota.
- Mỗi loại ảnh một thang chấm ngắn riêng: nền (không người, không chữ, đúng style, có đường mặt đất, đúng thời kỳ); ảnh nhân vật (khớp bộ đã duyệt, đúng tư thế, nền trong suốt sạch); đạo cụ.
- Code lọc trước khi gửi AI: sai kích thước, nền chưa tách được, ảnh trùng.
- **[Claude quyết]** Bắt đầu với agy (gói Ultra). Thiết kế để đổi sang Gemini API bằng cấu hình, không phải viết lại.
- Lỗi review hiện bằng tiếng Việt.

### 4.10 Dashboard

Dashboard mới chỉ cho video dài; thanh job và ô Claude ở dưới cùng giữ như cũ. Năm màn hình (bản phác: `.superpowers/brainstorm/34991-1793441859/content/layout-v2.html`), ghép từ cách làm của Kitsu/ShotGrid, Frame.io, LTX Studio, ElevenLabs Dubbing, Linear:

1. **Trang chủ**: hộp "🔔 Cần bạn" gom mọi việc chờ chủ kênh ở mọi dự án (ảnh 3/5, kịch bản chờ chốt, tên chưa có phiên âm, giọng thiếu…), mỗi dòng bấm vào là tới đúng chỗ; danh sách dự án với tiến độ và ngôn ngữ; nút "Video mới".
2. **Trang dự án**: thanh bước ở trên; dòng trạng thái từng ngôn ngữ; **bảng cảnh theo câu** ở giữa (câu, nền, nhân vật, chuyển động, âm thanh, trạng thái); bấm một dòng thì xem trước Remotion của câu đó.
3. **Hàng duyệt ảnh**: lưới ảnh hiện ngay khi có điểm; ảnh lớn kèm lỗi; phím `A` duyệt, `R` vẽ lại kèm ghi chú, `←/→` chuyển ảnh; chọn nhiều để duyệt một lần; lọc "cần bạn".
4. **Thư viện**: bộ nhân vật quan trọng, kiểu đám đông, nền dùng lại; tạo tư thế mới từ ảnh gốc.
5. **Ngôn ngữ**: tab mỗi ngôn ngữ, nút "+"; câu gốc cạnh câu dịch; cảnh báo tự động (thiếu câu, thiếu số, tên chưa có phiên âm).
Cộng màn hình **Kịch bản** dạng chat ở mục 4.4.

## 5. Các quyết định Claude đã tự đưa ra (chủ kênh xem lại)

- Bố cục thư mục `projects/` + `lang/<mã>/` + `library/` + cấu hình ngôn ngữ chung.
- Mỗi video chỉ nêu 1–3 chỗ các nguồn vênh nhau.
- Nhân vật quan trọng do AI vẽ thành bộ ảnh rời (không vẽ bằng code); ranh giới hạng = có tên và xuất hiện từ 2 cảnh.
- Review bắt đầu với agy, sẵn đường đổi sang Gemini API.
- AI đề xuất hiệu ứng âm thanh cho từng câu, chủ kênh sửa.
- Skill `yt-*` cũ chuyển vào archive, phần dùng được chép sang hướng dẫn mới.
- Nguồn trong ngân hàng dữ kiện có thể là trang web **hoặc file chủ kênh tải lên** (PDF, ảnh scan sách, bản dịch chính sử). Với file, dữ kiện lưu số trang và đoạn trích; Gemini kiểm trên chính file đó. Chủ kênh không bắt buộc phải tải sách; thiếu nguồn A thì câu đó vàng và chủ kênh quyết.
- Bản đồ: nền là đường bờ biển ngày nay, ghi nhỏ trên màn hình rằng đó là bản đồ hiện đại khi địa hình xưa khác nhiều (ví dụ cửa sông Bạch Đằng năm 1288). Mặc định chỉ dùng địa danh, mũi tên, vùng tô gần đúng; chỉ vẽ đường biên lịch sử khi ngân hàng dữ kiện có mô tả đủ cụ thể (các điểm mốc nêu trong nguồn), vẽ lại bằng code, không đồ từ bản đồ của người khác.
- Bản dịch ja/de/es được render khi qua hết kiểm tự động và model thứ hai đồng ý; chủ kênh không cần đọc. Câu bị cảnh báo hiện trong "Cần bạn" kèm bản dịch ngược sang tiếng Việt để chủ kênh quyết.

## 6. Để người xây quyết

- Dashboard mới viết lại hay sửa từ `dashboard/server.py` + `index.html` hiện có; công nghệ giao diện; cách lưu trạng thái (miễn là trên đĩa, chịu được tạm dừng và tắt máy).
- Cấu trúc file ngân hàng dữ kiện, kịch bản, cảnh; cách gắn câu với dữ kiện.
- Cách dò thời điểm từng câu cho chắc với cả 5 ngôn ngữ (dò khoảng lặng như hiện có; tiếng Nhật cần thử kỹ).
- Nguồn hiệu ứng âm thanh có giấy phép và cách đặt mức âm lượng.
- Cách tách nền nhân vật (vẽ trên nền một màu phẳng rồi tách bằng code; không dùng nền trắng vì áo trắng bị mất), điểm neo, khớp tỉ lệ nhân vật với chiều sâu của nền.
- Bộ component Remotion cho đám đông, nhân vật quan trọng, bản đồ, thẻ chữ; tái dùng `tools/anim` tới đâu.
- Cách kiểm "câu có nêu sự kiện không" (luật, model, hay cả hai).
- Thứ tự xây và cách làm thử; nên có một thử nghiệm sớm (1 nền + 1 nhân vật quan trọng + 1 đoàn người que + 10 giây Remotion) để xem lớp ghép có "liền" với nền không trước khi xây toàn bộ.

## 7. Để sau

- n8n; chuyển workflow sang máy Windows (đã rà: các chỗ phụ thuộc macOS là `sips`, 4 tool Swift, 6 script `.sh`, đường dẫn cứng, `caffeinate`).
- Gemini API thay agy.
- Upload YouTube tự động.
- Đề tài video dài đầu tiên: đề xuất Mông–Nguyên / bẫy cọc Bạch Đằng 1288 (chưa chốt).
