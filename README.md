# YouTube Production Engine

Skill sản xuất video dùng chung cho Gemini, Codex và agent có khả năng đọc skill/chạy lệnh. Cấu hình từng hướng video bằng profile riêng, không cần sửa bộ máy.

Quy trình: nghiên cứu → script → voice → cảnh/prompt ảnh → metadata → dựng MP4.

- `paleon`: nội dung về người tiền sử, phong cách doodle, narration tiếng Anh.
- `general-explainer`: hồ sơ explainer trung tính để bắt đầu.
- `profiles/template.json`: mẫu tạo hướng mới.

## Cài đặt

Clone hoặc tải ZIP, rồi đặt thư mục repo vào nơi agent tìm skill:

- Codex: `$CODEX_HOME/skills/youtube-production-engine` hoặc `~/.codex/skills/youtube-production-engine`.
- Gemini: thư mục skill mà bản Gemini của bạn hỗ trợ; thiết lập nguồn dùng `~/.gemini/config/skills/youtube-production-engine`.

Xem [INSTALL.md](INSTALL.md) để biết cách gọi bằng lời. Agent khác có thể đọc [SKILL.md](SKILL.md) trực tiếp.

Máy cần Python 3.11–3.13. Lần đầu dùng voice/render cần internet:

```sh
python scripts/engine.py doctor
python scripts/engine.py bootstrap
```

Thư viện cài trong virtual environment riêng, model Kokoro tự tải vào cache (~354 MB) và kiểm tra SHA-256. Repo không chứa model hoặc tài khoản dịch vụ. Tạo ảnh/research sử dụng công cụ có sẵn của agent. Voice local hiện hỗ trợ tiếng Anh; ngôn ngữ khác dùng provider bên ngoài và WAV/SRT tương ứng.

Renderer hỗ trợ ảnh tĩnh, cắt cảnh, letterbox và narration; xuất H.264/AAC MP4. Chưa tự chèn logo, nhạc hoặc phụ đề cháy. Không cần CapCut.

## Kiểm tra

```sh
python -B -m unittest discover -s tests -v
```

11 test tự động và mẫu tích hợp tải model → voice/SRT → MP4 đã chạy thành công trên Windows/Python 3.13. macOS/Linux là mục tiêu hỗ trợ, chưa được chạy thử. Kiểm tra kỹ thuật không thay thế nghe giọng, xem hình và review nội dung.

Hướng dẫn chi tiết: [runtime](references/runtime.md), [profiles](references/profiles.md), [production](references/production.md), [editorial](references/editorial.md). Nguồn và giấy phép thành phần: [THIRD_PARTY.md](THIRD_PARTY.md).
