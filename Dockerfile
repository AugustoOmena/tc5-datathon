FROM public.ecr.aws/lambda/python:3.10

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/api ./src/api
COPY feature_repo ./feature_repo

ENV PYTHONPATH=${LAMBDA_TASK_ROOT}

CMD ["src.api.main.handler"]