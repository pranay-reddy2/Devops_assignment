output "vpc_id" {
  description = "ID of the VPC."
  value       = aws_vpc.main.id
}

output "public_subnet_id" {
  description = "ID of the public subnet."
  value       = aws_subnet.public.id
}

output "availability_zone" {
  description = "AZ of the public subnet and the instance."
  value       = aws_subnet.public.availability_zone
}

output "security_group_id" {
  description = "ID of the web security group."
  value       = aws_security_group.web.id
}

output "instance_id" {
  description = "ID of the EC2 instance."
  value       = aws_instance.web.id
}

output "instance_public_ip" {
  description = "Public IP of the web server."
  value       = aws_instance.web.public_ip
}

output "web_url" {
  description = "URL of the nginx page served by the instance."
  value       = "http://${aws_instance.web.public_dns}"
}

output "assets_bucket" {
  description = "Name of the S3 bucket."
  value       = aws_s3_bucket.assets.bucket
}
