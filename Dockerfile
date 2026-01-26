# Use the official Azure Functions Python base image
FROM mcr.microsoft.com/azure-functions/python:4-python3.11

# Set the working directory
ENV AzureWebJobsScriptRoot=/home/site/wwwroot \
    AzureFunctionsJobHost__Logging__Console__IsEnabled=true

# Copy the requirements file and install dependencies
COPY requirements.txt /home/site/wwwroot/
RUN cd /home/site/wwwroot && \
    pip install --no-cache-dir -r requirements.txt

# Copy the function app files
COPY function_app.py /home/site/wwwroot/
COPY host.json /home/site/wwwroot/
COPY csv_schemas.json /home/site/wwwroot/

# Expose the port that Azure Functions uses
EXPOSE 80

# The base image already has the command to start the Functions host