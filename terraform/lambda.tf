# IAM Role para o Lambda
resource "aws_iam_role" "lambda_role" {
  name = "tc5_lambda_role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
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