# Cài và dùng

Giải nén để có một thư mục `youtube-production-engine` chứa `SKILL.md`.

- **Gemini:** chép thư mục vào nơi Gemini của bạn tìm skill. Với cách bố trí đang dùng, đó là `~/.gemini/config/skills/`.
- **Codex:** chép thư mục vào `$CODEX_HOME/skills/`, hoặc `~/.codex/skills/` khi chưa đặt CODEX_HOME.
- **Agent khác:** đưa agent đọc `SKILL.md`; agent cần công cụ chạy lệnh để thực thi phần voice/dựng video.

Mở phiên mới hoặc tải lại danh sách skill nếu agent chưa nhận ra skill mới. Gói không chứa đường dẫn máy cá nhân và không sửa skill Paleon cũ.

## Gọi bằng lời

```text
Dùng youtube-production-engine, profile paleon, làm video về cách người tiền sử chăm sóc người bị thương.
```

```text
Dùng youtube-production-engine tạo profile mới về [chủ đề], cho [người xem], bằng [ngôn ngữ]. Chưa sản xuất video.
```

```text
Dùng youtube-production-engine, profile general-explainer, chỉ nghiên cứu và viết kịch bản về [câu hỏi].
```

## Lần chạy đầu

Máy cần Python 3.11–3.13 và internet cho bước chuẩn bị voice/render. Từ thư mục skill:

```text
python scripts/engine.py doctor
python scripts/engine.py bootstrap
```

Agent có thể chạy các lệnh này thay bạn. Thư viện cài trong môi trường riêng ở cache người dùng. Model Kokoro tải ở lần tạo voice đầu (~354 MB) và được kiểm tra SHA-256. Các lần sau dùng lại cache. Nếu tên lệnh trên máy là `python3` hoặc `py -3.13`, dùng tên tương ứng.

Skill không kèm dịch vụ tạo ảnh, tài khoản API hay Python. Research/tạo ảnh dùng công cụ có sẵn của agent. Khi thiếu công cụ tạo ảnh, skill xuất prompt để bạn tạo ảnh rồi tiếp tục dựng. Voice local hiện hỗ trợ tiếng Anh; ngôn ngữ khác dùng hồ sơ `external` và cung cấp WAV/SRT tương ứng. CapCut không bắt buộc.

Có sẵn hai hồ sơ dùng được: `paleon` và `general-explainer`. Muốn hướng riêng, tạo một file từ `profiles/template.json`, hoàn thiện nội dung và đặt `ready: true`; không cần sửa script. File hướng dẫn chi tiết được liên kết từ `SKILL.md`.
