provider "aws" {
  region = "us-east-1"
  profile = "envdev"
}

# Bucket S3 para armazenar tudo: Dados brutos, Parquets do Feast e Modelos
resource "aws_s3_bucket" "mlops_artifacts" {
  bucket = "tc5-mlops-artifacts-${random_id.suffix.hex}"
}

resource "random_id" "suffix" {
  byte_length = 4
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
        Effect   = "Allow"
        Resource = [
          "${aws_s3_bucket.mlops_artifacts.arn}",
          "${aws_s3_bucket.mlops_artifacts.arn}/*"
        ]
      }
    ]
  })
}

# Saída do nome do bucket para usarmos depois
output "s3_bucket_name" {
  value = aws_s3_bucket.mlops_artifacts.bucket
}