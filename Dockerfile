FROM python:3.10-slim

# Install AWS Lambda Runtime Interface Client for Python
RUN pip install --no-cache-dir aws-lambda-powertools awslambdaric

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/api /var/task/src/api
COPY feature_repo /var/task/feature_repo

WORKDIR /var/task
ENV PYTHONPATH=/var/task

# Set the CMD to be the Lambda handler
ENTRYPOINT ["/usr/local/bin/python", "-m", "awslambdaric"]
CMD ["src.api.main.handler"]