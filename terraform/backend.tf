terraform {
  backend "s3" {
    bucket = "tc5-mlops-artifacts-f4d7a3e1"
    key    = "terraform/state/terraform.tfstate"
    region = "us-east-1"
  }
}