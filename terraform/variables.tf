variable "aws_region" {
  description = "AWS region for CloudTask infrastructure."
  type        = string
  default     = "ap-south-1"
}

variable "project_name" {
  description = "Project name used in resource names and tags."
  type        = string
  default     = "cloudtask"
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
  default     = "dev"
}

variable "vpc_cidr" {
  description = "CIDR range for the CloudTask VPC."
  type        = string
  default     = "10.30.0.0/16"
}

variable "public_subnet_cidr" {
  description = "CIDR range for the public application subnet."
  type        = string
  default     = "10.30.1.0/24"
}

variable "instance_type" {
  description = "EC2 instance size."
  type        = string
  default     = "t3.micro"

  validation {
    condition     = contains(["t2.micro", "t3.micro"], var.instance_type)
    error_message = "instance_type must be t2.micro or t3.micro."
  }
}

variable "ssh_cidr" {
  description = "Your public IP in CIDR notation, for example 203.0.113.10/32."
  type        = string
}

variable "monitoring_cidr" {
  description = "Trusted CIDR allowed to reach Prometheus, Grafana, and Node Exporter."
  type        = string
}

variable "app_port" {
  description = "CloudTask application port exposed on the instance."
  type        = number
  default     = 5000

  validation {
    condition     = contains([5000, 8000], var.app_port)
    error_message = "app_port must be 5000 or 8000."
  }
}

variable "key_name" {
  description = "Name for the EC2 key pair."
  type        = string
  default     = "cloudtask-ap-south-1"
}

variable "public_key" {
  description = "OpenSSH public key uploaded to EC2. Keep the private key outside Terraform."
  type        = string
  sensitive   = true
}

variable "bucket_name" {
  description = "Optional globally unique S3 bucket name. Leave empty to generate one."
  type        = string
  default     = ""
}

variable "monthly_budget_limit" {
  description = "Monthly AWS spend limit in USD."
  type        = number
  default     = 25

  validation {
    condition     = var.monthly_budget_limit > 0
    error_message = "monthly_budget_limit must be greater than zero."
  }
}

variable "budget_email" {
  description = "Email address for AWS Budget notifications."
  type        = string
}
