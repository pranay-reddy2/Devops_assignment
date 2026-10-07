resource "aws_s3_bucket" "yatri117" {
  bucket        = var.bucket_name
  force_destroy = true
  tags = {
    Name        = var.bucket_name
    Environment = "dev"
    ManagedBy   = "Terraform"
    Project     = "Session18"
  }
}

# Keep every object version (protects against overwrite/delete mistakes).
resource "aws_s3_bucket_versioning" "yatri117" {
  bucket = aws_s3_bucket.yatri117.id
  versioning_configuration {
    status = "Enabled"
  }
}

# New buckets already block public access by default; making it explicit keeps it
# enforced even if someone changes the account defaults.
resource "aws_s3_bucket_public_access_block" "yatri117" {
  bucket                  = aws_s3_bucket.yatri117.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
