FROM mcr.microsoft.com/azure-functions/python:4-python3.11
 
ENV AzureWebJobsScriptRoot=/home/site/wwwroot \
    AzureFunctionsJobHost__Logging__Console__IsEnabled=true
 
COPY function_app.py /home/site/wwwroot/
COPY host.json /home/site/wwwroot/
COPY requirements.txt /home/site/wwwroot/
 
RUN cd /home/site/wwwroot && \
    pip install --no-cache-dir -r requirements.txt