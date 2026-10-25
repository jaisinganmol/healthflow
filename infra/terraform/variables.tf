variable "aws_region" {
  type        = string
  default     = "us-east-1"
  description = "AWS region for HIPAA-compliant infrastructure"
}

variable "environment" {
  type        = string
  default     = "production"
  description = "Deployment environment name (production, staging, dev)"
}

variable "retention_days" {
  type        = number
  default     = 2190 # 6 years statutory HIPAA retention period
  description = "WORM compliance lock retention period in days"
}
