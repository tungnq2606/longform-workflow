# Xưởng làm video YouTube (nhiều kênh)

Mở dashboard: `dashboard/start.sh` rồi vào http://127.0.0.1:8765. Mọi bước làm video đều có trên dashboard.

Mỗi kênh một thư mục trong `channels/`:
- `channels/median-worker/`: The Median Worker (tiền bạc đời thường). Tài liệu chiến lược ở `docs/`.
- `channels/fossil-receipts/`: Fossil Receipts (con người thời tiền sử).

Trong mỗi kênh:
- `channel.json`: tên, handle, mô tả ngắn, style ảnh;
- `CHANNEL_SETUP.md`: chữ để dán vào YouTube Studio và cài đặt kênh;
- `brand/`: avatar, banner, watermark;
- `research/`: kết quả đo cụm từ và nghiên cứu của Gemini;
- `videos/NNN-ten-ngan/`: từng video. Xem `VIDEO.md` trong đó để biết video đang ở bước nào.

Dùng chung cho mọi kênh:
- `tools/`: công cụ;
- `templates/`: khung cho video mới (`video/`) và kênh mới (`channel/`);
- `dashboard/`: dashboard;
- `LICENSES.md`: giấy phép font, giọng đọc, nhạc, ảnh.

Thêm kênh mới (có thể dùng style hình khác): làm theo `templates/channel/README.md`. Kênh mới tự hiện trên dashboard.

Lệnh tay:
- Tạo video: `tools/pipeline/new_video.sh fossil-receipts 003 ten-ngan`
- Tạo text giọng đọc: `python3 tools/pipeline/voice_text.py channels/<kênh>/videos/003-ten-ngan`
