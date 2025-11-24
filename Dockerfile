# 1. Python base image (ổn định)
FROM python:3.10-slim

# 2. Tạo thư mục ứng dụng
WORKDIR /app

# 3. Copy file requirements trước (tối ưu cache)
COPY requirements.txt /app/

# 4. Cài dependency
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy toàn bộ source code vào image
COPY . /app