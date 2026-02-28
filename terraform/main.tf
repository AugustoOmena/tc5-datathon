variable "aws_region" {
  description = "AWS region where resources will be created"
  type        = string
  default     = "us-east-1" # alterado para manter lambda e bucket na mesma região
}

provider "aws" {
  region = var.aws_region
}

# Bucket S3 para armazenar tudo: Dados brutos, Parquets do Feast e Modelos
resource "aws_s3_bucket" "mlops_artifacts" {
  bucket = "tc5-mlops-artifacts-${random_id.suffix.hex}"
}

resource "random_id" "suffix" {
  byte_length = 4
}

resource "random_id" "mlflow_suffix" {
  byte_length = 4
}

# bucket for MLflow artifact store (useful quando estamos rodando MLflow server externo)
resource "aws_s3_bucket" "mlflow_artifacts" {
  bucket = "tc5-mlflow-artifacts-${random_id.mlflow_suffix.hex}"
}


# Criando a estrutura de pastas dentro do S3
resource "aws_s3_object" "folder_data" {
  bucket = aws_s3_bucket.mlops_artifacts.id
  key    = "data/"
}

resource "aws_s3_object" "folder_models" {
  bucket = aws_s3_bucket.mlops_artifacts.id
  key    = "models/"
}

resource "aws_iam_policy" "ml_engineer_s3_policy" {
  name        = "TC5_ML_Engineer_S3_Policy"
  description = "Permite que o engenheiro de ML suba modelos e dados para o S3"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:ListBucket",
          "s3:DeleteObject"
        ]
        Effect = "Allow"
        Resource = [
          "${aws_s3_bucket.mlops_artifacts.arn}",
          "${aws_s3_bucket.mlops_artifacts.arn}/*",
          "${aws_s3_bucket.mlflow_artifacts.arn}",
          "${aws_s3_bucket.mlflow_artifacts.arn}/*"
        ]
      }
    ]
  })
}

# Saída do nome do bucket para usarmos depois
output "s3_bucket_name" {
  value = aws_s3_bucket.mlops_artifacts.bucket
}

output "mlflow_bucket_name" {
  value       = aws_s3_bucket.mlflow_artifacts.bucket
  description = "Bucket onde artefatos do MLflow serão armazenados (artifacts)"
}