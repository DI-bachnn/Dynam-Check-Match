FROM mcr.microsoft.com/azure-functions/python:4-python3.10
WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app