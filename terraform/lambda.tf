# IAM Role para o Lambda
resource "aws_iam_role" "lambda_role" {
  name = "tc5_lambda_role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

# Permissão para o Lambda escrever logs no CloudWatch (obrigatório para ver logs)
resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Permissão para o Lambda ler do S3 (seu bucket de artefatos)
resource "aws_iam_role_policy_attachment" "s3_read" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"
}

# Função Lambda usando a imagem do ECR
resource "aws_lambda_function" "api_lambda" {
  function_name = "tc5-prediction-api"
  role          = aws_iam_role.lambda_role.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.api_repo.repository_url}:latest"
  timeout       = 60
  memory_size   = 512

  # Garanta que o handler seja passado exatamente assim
  image_config {
    command = ["src.api.main.handler"]
  }

  environment {
    variables = {
      FEAST_REPO_PATH = "/var/task/feature_repo"
      S3_BUCKET_NAME  = aws_s3_bucket.mlops_artifacts.bucket
    }
  }
}

resource "aws_cloudwatch_log_group" "lambda_log" {
  name              = "/aws/lambda/tc5-prediction-api"
  retention_in_days = 7
}

# policy allowing the Lambda to send custom metrics to CloudWatch
resource "aws_iam_role_policy" "lambda_cw_metric" {
  name = "tc5_lambda_put_metrics"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData"
        ]
        Resource = "*"
      }
    ]
  })
}

# Dashboard for model monitoring and drift
resource "aws_cloudwatch_dashboard" "model_drift" {
  dashboard_name = "tc5-model-monitoring"
  dashboard_body = <<DASH
{
  "widgets": [
    {
      "type": "metric",
      "x": 0,
      "y": 0,
      "width": 24,
      "height": 6,
      "properties": {
        "metrics": [
          [ "TC5/Model", "PredictionValue" ],
          [ "TC5/Model", "PredictionCount" ]
        ],
        "period": 300,
        "view": "timeSeries",
        "region": "us-east-1"
      }
    }
  ]
}
DASH
}
