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

# Enable versioning for data protection
resource "aws_s3_bucket_versioning" "app_data_versioning" {
  bucket = aws_s3_bucket.app_data.id
  versioning_configuration {
    status = "Enabled"
  }
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