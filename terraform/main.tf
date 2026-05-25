terraform {
  backend "s3" {
    bucket         = "prima-tf-state-094508075399"
    key            = "app-infrastructure/terraform.tfstate"
    region         = "eu-west-1"
    dynamodb_table = "prima-tf-lock"
    encrypt        = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}


# ---------------------------------------------------
# Data Sources: Look up existing AWS infrastructure
# ---------------------------------------------------
data "aws_caller_identity" "current" {}

data "aws_eks_cluster" "existing_cluster" {
  name = "prima-eks-cluster"
}

# Dynamically construct the OIDC Provider ARN from the cluster data
locals {
  oidc_provider_url = replace(data.aws_eks_cluster.existing_cluster.identity[0].oidc[0].issuer, "https://", "")
  oidc_provider_arn = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/${local.oidc_provider_url}"
}

# ---------------------------------------------------
# Amazon S3 Bucket
# ---------------------------------------------------
resource "aws_s3_bucket" "app_data" {
  # Ensure S3 bucket name is globally unique
  bucket = "prima-tech-challenge-data-${random_id.bucket_suffix.hex}"

  tags = {
    Environment = "Challenge"
    ManagedBy   = "Terraform"
  }
}

# Generate a random string to ensure the bucket name is globally unique
resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# Security best practice: Block all public access by default
resource "aws_s3_bucket_public_access_block" "app_data_access" {
  bucket = aws_s3_bucket.app_data.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}


# ---------------------------------------------------
# Amazon DynamoDB Table
# ---------------------------------------------------
resource "aws_dynamodb_table" "app_state" {
  name = "prima-user-db"

  # Utilizing the AWS Free Tier (Max 25 RCU / 25 WCU per month)
  billing_mode   = "PROVISIONED"
  read_capacity  = 5
  write_capacity = 5

  hash_key = "id"

  attribute {
    name = "id"
    type = "S"
  }

  tags = {
    Environment = "Challenge"
    ManagedBy   = "Terraform"
  }
}


# 1. Create the IAM Policy for DynamoDB Access
resource "aws_iam_policy" "dynamodb_access" {
  name        = "prima-flask-dynamodb-policy"
  description = "Allows Flask app to write to the state table"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem"
        ]
        # References the table you created earlier
        Resource = aws_dynamodb_table.app_state.arn
      }
    ]
  })
}

# 2. Use the official AWS module to easily create the IRSA Role
module "iam_eks_role" {
  source    = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version   = "~> 5.0"
  role_name = "prima-flask-app-role"
  role_policy_arns = {
    dynamodb = aws_iam_policy.dynamodb_access.arn
  }
  oidc_providers = {
    main = {
      # Use the dynamically constructed ARN from the local variables above
      provider_arn               = local.oidc_provider_arn
      namespace_service_accounts = ["default:flask-app-sa"]
    }
  }
}

# 3. Output the Role ARN so we can use it in Helm
output "flask_irsa_role_arn" {
  value = module.iam_eks_role.iam_role_arn
}