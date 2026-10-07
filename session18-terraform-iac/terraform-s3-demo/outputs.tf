output "bucket_name" {
  type        = string
  description = "Name of the S3 bucket."
  value       = aws_s3_bucket.yatri117.bucket
}
output "bucket_arn" {
  type        = string
  description = "ARN of the S3 bucket."
  value       = aws_s3_bucket.yatri117.arn
}
output "bucket_region" {
  type        = string
  description = "AWS region of the S3 bucket."
  value       = aws_s3_bucket.yatri117.region
}

output "versioning_status" {
  type        = string
  description = "Versioning state of the bucket."
  value       = aws_s3_bucket_versioning.yatri117.versioning_configuration[0].status
}
