# Sử dụng Python nhẹ làm base image
FROM python:3.10-slim

# Thiết lập thư mục làm việc trong container
WORKDIR /app

# Copy file requirements.txt (chứa các package cần cài)
COPY requirements.txt .

# Cài các package trong requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ code của bạn vào container
COPY . .

# Expose port (chỉ cần nếu test local)
EXPOSE 80

# Lệnh chạy Azure Function
CMD ["func", "start", "--python"]
