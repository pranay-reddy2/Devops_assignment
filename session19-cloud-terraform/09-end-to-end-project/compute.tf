# Latest Amazon Linux 2023 AMI for the region, resolved from AWS's public SSM parameter.
data "aws_ssm_parameter" "al2023" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

resource "aws_instance" "web" {
  ami                    = data.aws_ssm_parameter.al2023.value
  instance_type          = var.instance_type
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.web.id]

  # IMDSv2 only (blocks SSRF-style credential theft through the metadata service).
  metadata_options {
    http_tokens   = "required"
    http_endpoint = "enabled"
  }

  root_block_device {
    volume_type = "gp3"
    volume_size = 8
    encrypted   = true
  }

  user_data = templatefile("${path.module}/user-data.sh.tftpl", {
    project = var.project
    bucket  = aws_s3_bucket.assets.bucket
  })
  user_data_replace_on_change = true

  # Explicit dependency: the instance should only boot once the subnet can reach the
  # internet (dnf install needs it). Terraform cannot infer this from references.
  depends_on = [aws_route_table_association.public]

  tags = { Name = "${var.project}-web" }
}
