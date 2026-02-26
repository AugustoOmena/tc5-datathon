resource "aws_ecr_repository" "api_repo" {
  name                 = "tc5-api-repo"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

output "ecr_repository_url" {
  value = aws_ecr_repository.api_repo.repository_url
}