variable "aws_region" {
  description = "AWS region for all resources."
  type        = string
  default     = "ap-south-1"
}

variable "project" {
  description = "Name prefix for resources."
  type        = string
  default     = "session19-e2e"
}

variable "owner" {
  description = "Owner tag."
  type        = string
  default     = "pranay-reddy"
}

variable "vpc_cidr" {
  description = "CIDR block of the VPC."
  type        = string
  default     = "10.30.0.0/16"
}

variable "public_subnet_cidr" {
  description = "CIDR block of the public subnet (must be inside vpc_cidr)."
  type        = string
  default     = "10.30.1.0/24"

  validation {
    condition     = can(cidrhost(var.public_subnet_cidr, 0))
    error_message = "public_subnet_cidr must be a valid CIDR block."
  }
}

variable "instance_type" {
  description = "EC2 instance type (free-tier eligible by default)."
  type        = string
  default     = "t3.micro"
}

variable "allowed_http_cidrs" {
  description = "Who may reach the web server on port 80."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}
