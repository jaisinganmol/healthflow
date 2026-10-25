terraform {
  required_version = ">= 1.8.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.50"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# -----------------------------------------------------------------------------
# 1. Immutable Audit Log Bucket with Object Lock (WORM - 6-Year Retention)
# -----------------------------------------------------------------------------
resource "aws_s3_bucket" "audit_log_worm" {
  bucket              = "healthflow-audit-trail-worm-${var.environment}"
  object_lock_enabled = true

  tags = {
    Environment = var.environment
    Compliance  = "HIPAA-6-Year-WORM"
    ManagedBy   = "Terraform"
  }
}

resource "aws_s3_bucket_object_lock_configuration" "audit_lock" {
  bucket = aws_s3_bucket.audit_log_worm.id

  rule {
    default_retention {
      mode = "COMPLIANCE" # Unbreakable compliance mode (cannot be deleted or shortened even by root)
      days = var.retention_days
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "audit_encryption" {
  bucket = aws_s3_bucket.audit_log_worm.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "audit_private" {
  bucket = aws_s3_bucket.audit_log_worm.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# -----------------------------------------------------------------------------
# 2. AWS SQS FIFO Queues for Event-Driven Ingestion (Admit / Discharge)
# -----------------------------------------------------------------------------
resource "aws_sqs_queue" "admissions_fifo" {
  name                        = "healthflow-admissions-${var.environment}.fifo"
  fifo_queue                  = true
  content_based_deduplication = true
  kms_master_key_id           = "alias/aws/sqs"
  visibility_timeout_seconds  = 300
}

resource "aws_sqs_queue" "discharges_fifo" {
  name                        = "healthflow-discharges-${var.environment}.fifo"
  fifo_queue                  = true
  content_based_deduplication = true
  kms_master_key_id           = "alias/aws/sqs"
  visibility_timeout_seconds  = 300
}

# -----------------------------------------------------------------------------
# 3. AWS Aurora PostgreSQL for Durable LangGraph Checkpointing
# -----------------------------------------------------------------------------
resource "aws_rds_cluster" "checkpoint_db" {
  cluster_identifier      = "healthflow-checkpointer-${var.environment}"
  engine                  = "aurora-postgresql"
  engine_version          = "16.1"
  database_name           = "healthflow"
  master_username         = "healthflow_admin"
  manage_master_user_password = true
  storage_encrypted       = true
  deletion_protection     = true
  backup_retention_period = 30

  tags = {
    Environment = var.environment
    Compliance  = "HIPAA-Encrypted"
  }
}
