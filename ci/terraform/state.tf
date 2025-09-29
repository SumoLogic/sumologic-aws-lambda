terraform {
  required_version = ">= 0.13"

  backend "s3" {
    bucket = "replicon-cd-terraform-remote-state-storage-s3"
    key    = "terraform/sumologic-aws-lambda/terraform.tfstate"
    region = "us-east-1"
  }
}