output "ec2_public_ip" {
  description = "Public IPv4 address of the CloudTask EC2 instance."
  value       = aws_instance.app.public_ip
}

output "bucket_name" {
  description = "S3 bucket for CloudTask backups and static assets."
  value       = aws_s3_bucket.assets.bucket
}

output "vpc_id" {
  description = "CloudTask VPC ID."
  value       = aws_vpc.main.id
}
