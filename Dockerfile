# Sử dụng image Python nhẹ nhất
FROM python:3.11-slim

# Thiết lập thư mục làm việc
WORKDIR /app

# Copy requirement
COPY requirements.txt .

# Cài đặt thư viện
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ mã nguồn
COPY . .

# Expose port (tùy thuộc vào PORT environment)
EXPOSE 5000

# Khởi chạy server bằng Gunicorn thay vì Flask development server (tốt cho production)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
