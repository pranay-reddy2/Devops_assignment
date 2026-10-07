# S3 bucket names are global, so add a random suffix.
resource "random_id" "suffix" {
  byte_length = 4
}

resource "aws_s3_bucket" "assets" {
  bucket        = "${var.project}-assets-${random_id.suffix.hex}"
  force_destroy = true # lab only: lets terraform destroy remove a non-empty bucket

  tags = { Name = "${var.project}-assets" }
}

resource "aws_s3_bucket_versioning" "assets" {
  bucket = aws_s3_bucket.assets.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "assets" {
  bucket = aws_s3_bucket.assets.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "assets" {
  bucket                  = aws_s3_bucket.assets.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_object" "readme" {
  bucket       = aws_s3_bucket.assets.id
  key          = "deployments/session19.txt"
  content      = "Deployed by Terraform for ${var.project} into ${aws_vpc.main.id}\n"
  content_type = "text/plain"
}
