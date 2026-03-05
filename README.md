# Backlog Translator Webhook

Server này là một Webhook nhận các sự kiện từ Backlog (khi tạo Issue mới), sau đó dùng OpenAI để dịch nội dung từ tiếng Nhật sang tiếng Việt và comment trực tiếp vào ticket đó.

## Cách chạy Local (để test)

1. Tạo môi trường ảo (khuyên dùng):
   ```bash
   python -m venv venv
   source venv/bin/activate  # Trên Mac/Linux
   ```

2. Cài đặt thư viện:
   ```bash
   pip install -r requirements.txt
   ```

3. Cấu hình biến môi trường:
   Đổi tên file `.env.example` thành `.env` và điền các API Key của bạn vào.

4. Chạy server:
   ```bash
   python app.py
   ```
   Server sẽ chạy ở `http://localhost:5000`. Để test Webhook từ máy local lên Backlog, bạn có thể dùng `ngrok` (chạy `ngrok http 5000` để lấy public URL).

## Cách 1: Build và Deploy bằng Docker (Khuyên dùng cho Server / VPS)

Nếu bạn có một Server (Ubuntu, CentOS...) hoặc VPS cài sẵn Docker:

1. Build Docker image:
   ```bash
   docker build -t backlog-webhook .
   ```

2. Chạy Docker container:
   ```bash
   docker run -d -p 5000:5000 \
     -e BACKLOG_API_KEY="your_key" \
     -e BACKLOG_BASE_URL="https://your_space.backlog.com/api/v2" \
     -e TARGET_USER="Nguyen Dieu Linh" \
     -e OPENAI_API_KEY="your_openai_key" \
     --name backlog-bot \
     backlog-webhook
   ```

## Cách 2: Deploy lên các nền tảng Cloud (Render / Railway / Heroku)

Bạn có thể đẩy code này lên một repository trên **GitHub**, sau đó kết nối vào các dịch vụ miễn phí như **Render.com** hoặc **Railway.app**:

- **Render.com**: Tạo "Web Service" -> Chọn repository GitHub -> Điền Build Command: `pip install -r requirements.txt` và Start Command: `gunicorn app:app`. Sau đó ở tab Environment, thêm các biến `BACKLOG_API_KEY`, `OPENAI_API_KEY`, v.v.
- **Vercel** cũng có thể chạy tuy nhiên sẽ cần setup lại theo kiểu serverless function của Vercel (bằng `vercel.json`). Do đó Render.com sẽ là cách dễ và nhanh nhất cho web app dùng Flask.

## Next Action trên Backlog
Sau khi đã có url của app (ví dụ: `https://your-app.onrender.com`), vào Backlog:
1. Vào **Project Settings** > **Webhooks**
2. **Add a webhook**
3. Mục **Webhook URL**: điền `https://your-app.onrender.com/webhook`
4. Mục **Events**: tick chọn **Issue Created**.
5. Save lại và tạo thử 1 ticket để test.
