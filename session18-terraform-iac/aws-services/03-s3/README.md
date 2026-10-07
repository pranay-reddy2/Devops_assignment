# Session 18 – AWS Services: S3 (Storage)

**Author:** Pranay Reddy
**Course:** SST DevOps & Cloud [SWE]
**Session:** 18, Task 2 (AWS Services Research)

All CLI commands in this file are reference commands (not run against a live account).

---

## What is S3?

Amazon Simple Storage Service (S3) is object storage: you store files ("objects") in containers ("buckets") and access them over HTTPS through an API. There are no disks or file systems to manage, and storage grows without provisioning.

Key properties:

- Designed for **99.999999999% (11 nines) durability**; most storage classes store data across at least three Availability Zones.
- **Strong read-after-write consistency** for all PUT, overwrite and DELETE operations.
- Buckets live in one Region; bucket names are globally unique.
- Pay for storage (GB-month), requests, data retrieval (some classes) and data transfer out.

S3 is the most common backend for Terraform remote state, static website assets, logs, backups and data lakes.

---

## Buckets

A bucket is the top-level container for objects.

- Name rules: 3–63 characters, lowercase letters, numbers, hyphens and dots, globally unique.
- Created in a chosen Region; data does not leave that Region unless you replicate it.
- Bucket types: **general purpose buckets** (the normal kind), **directory buckets** (for S3 Express One Zone), and **table buckets** (S3 Tables for Apache Iceberg).

Secure defaults for every new general purpose bucket (current behaviour):

| Setting | Default |
| :--- | :--- |
| S3 Block Public Access | All four settings **on** |
| Object Ownership | **Bucket owner enforced** (ACLs disabled) |
| Default encryption | **SSE-S3** applied to all new objects |
| SSE-C (customer-provided keys) | **Blocked** for new buckets since April 2026 unless explicitly enabled |

Because ACLs are disabled, access is controlled with IAM policies and bucket policies only.

```bash
aws s3api create-bucket --bucket pranay-devops-demo-2026 --region ap-south-1 \
  --create-bucket-configuration LocationConstraint=ap-south-1
aws s3api get-public-access-block --bucket pranay-devops-demo-2026
aws s3 ls
```

---

## Objects

An object is the stored data plus its metadata, addressed by a **key**.

- Key example: `logs/2026/10/07/app.log`. S3 has a flat namespace; the `/` only makes keys look like folders ("prefixes").
- Maximum object size: **50 TB** (raised from 5 TB in December 2025). A single PUT can upload up to 5 GB; larger objects use **multipart upload**.
- Each object has system metadata (size, ETag, storage class, encryption) and optional user metadata and up to 10 tags.

```bash
aws s3 cp ./build.zip s3://pranay-devops-demo-2026/artifacts/build.zip
aws s3api head-object --bucket pranay-devops-demo-2026 --key artifacts/build.zip
aws s3api list-objects-v2 --bucket pranay-devops-demo-2026 --prefix artifacts/
```

---

## Storage classes

| Storage class | Access pattern | Retrieval | Min. storage duration | AZs |
| :--- | :--- | :--- | :--- | :--- |
| S3 Standard | Frequent | Milliseconds | None | ≥3 |
| S3 Intelligent-Tiering | Unknown / changing | Milliseconds (optional archive tiers are slower) | None | ≥3 |
| S3 Express One Zone | Very frequent, latency-sensitive | Single-digit milliseconds | None | 1 (directory bucket) |
| S3 Standard-IA | Infrequent, needs fast access | Milliseconds, per-GB retrieval fee | 30 days | ≥3 |
| S3 One Zone-IA | Infrequent, re-creatable data | Milliseconds, per-GB retrieval fee | 30 days | 1 |
| S3 Glacier Instant Retrieval | Rare (about once a quarter), needs ms access | Milliseconds | 90 days | ≥3 |
| S3 Glacier Flexible Retrieval | Archive | Minutes to hours (expedited, standard, bulk) | 90 days | ≥3 |
| S3 Glacier Deep Archive | Long-term archive / compliance | Within 12 hours (standard) or 48 hours (bulk) | 180 days | ≥3 |

Notes:

- Intelligent-Tiering moves objects between tiers automatically for a small per-object monitoring fee; objects smaller than 128 KB are not monitored and stay in the frequent tier.
- Glacier Flexible Retrieval and Deep Archive objects must be **restored** before they can be read.

---

## Versioning

Versioning keeps every version of an object in the bucket.

- States: **unversioned** (default), **enabled**, **suspended**. Once enabled it can only be suspended, not turned off.
- Overwriting creates a new version ID; the old one stays.
- Deleting without a version ID adds a **delete marker**; the data is still there and can be recovered by removing the marker.
- Every version is billed, so pair versioning with lifecycle rules for non-current versions.
- Required for replication (CRR/SRR) and recommended for Terraform state buckets.
- **MFA Delete** and **S3 Object Lock** (WORM retention) add protection against deletion.

```bash
aws s3api put-bucket-versioning --bucket pranay-devops-demo-2026 \
  --versioning-configuration Status=Enabled
aws s3api list-object-versions --bucket pranay-devops-demo-2026 --prefix artifacts/
```

---

## Lifecycle policies

Lifecycle rules automate **transitions** (move to a cheaper class) and **expirations** (delete) based on object age, prefix, tags or size.

Example: logs move to Standard-IA after 30 days, Glacier Flexible Retrieval after 90 days, and are deleted after 365 days; old versions are cleaned up after 30 days; failed multipart uploads are aborted after 7 days.

```json
{
  "Rules": [
    {
      "ID": "logs-tiering-and-expiry",
      "Status": "Enabled",
      "Filter": { "Prefix": "logs/" },
      "Transitions": [
        { "Days": 30, "StorageClass": "STANDARD_IA" },
        { "Days": 90, "StorageClass": "GLACIER" }
      ],
      "Expiration": { "Days": 365 },
      "NoncurrentVersionExpiration": { "NoncurrentDays": 30 },
      "AbortIncompleteMultipartUpload": { "DaysAfterInitiation": 7 }
    }
  ]
}
```

`GLACIER` is the API name for Glacier Flexible Retrieval; `GLACIER_IR` and `DEEP_ARCHIVE` are the other archive classes.

```bash
aws s3api put-bucket-lifecycle-configuration --bucket pranay-devops-demo-2026 \
  --lifecycle-configuration file://lifecycle.json
```

---

## Encryption

| Type | Who manages the key | Notes |
| :--- | :--- | :--- |
| SSE-S3 | Amazon S3 | AES-256, **default for all new objects** at no extra cost |
| SSE-KMS | AWS KMS (AWS managed or customer managed key) | Key policies, CloudTrail audit of key use; enable **S3 Bucket Keys** to cut KMS request costs |
| DSSE-KMS | AWS KMS | Two independent layers of encryption for compliance needs |
| SSE-C | Customer supplies the key on every request | Disabled by default on new buckets since April 2026 |
| Client-side | Customer, before upload | S3 only sees ciphertext |

In transit, use HTTPS; a bucket policy can deny any request where `aws:SecureTransport` is `false`.

---

## Bucket policies

A bucket policy is a resource-based JSON policy attached to the bucket. It can grant access to other accounts or services, and it can enforce rules with Deny statements.

Example: allow CloudFront (Origin Access Control) to read objects, and deny any non-HTTPS request:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowCloudFrontRead",
      "Effect": "Allow",
      "Principal": { "Service": "cloudfront.amazonaws.com" },
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::pranay-devops-demo-2026/*",
      "Condition": {
        "StringEquals": {
          "AWS:SourceArn": "arn:aws:cloudfront::123456789012:distribution/EDFDVBD6EXAMPLE"
        }
      }
    },
    {
      "Sid": "DenyInsecureTransport",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": [
        "arn:aws:s3:::pranay-devops-demo-2026",
        "arn:aws:s3:::pranay-devops-demo-2026/*"
      ],
      "Condition": { "Bool": { "aws:SecureTransport": "false" } }
    }
  ]
}
```

This keeps Block Public Access on: the website is public through CloudFront while the bucket itself stays private.

```bash
aws s3api put-bucket-policy --bucket pranay-devops-demo-2026 --policy file://policy.json
aws s3api get-bucket-policy --bucket pranay-devops-demo-2026
```

---

## Common use cases

- **Terraform remote state** (versioned, encrypted bucket; S3 native state locking with `use_lockfile = true`).
- Static website / SPA assets served through CloudFront.
- Build artifacts and deployment packages from CI/CD pipelines.
- Application uploads (images, documents) using pre-signed URLs.
- Centralized logs (ALB, CloudTrail, VPC Flow Logs) and data lakes queried by Athena.
- Backups and long-term archives in Glacier classes.

Terraform snippet:

```hcl
resource "aws_s3_bucket" "demo" {
  bucket = "pranay-devops-demo-2026"
}

resource "aws_s3_bucket_versioning" "demo" {
  bucket = aws_s3_bucket.demo.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "demo" {
  bucket = aws_s3_bucket.demo.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "aws:kms" }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "demo" {
  bucket                  = aws_s3_bucket.demo.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
```

---

## Key takeaways

- S3 stores objects (key + data + metadata) in Regional buckets with 11 nines durability and strong consistency.
- New buckets are private by default: Block Public Access on, ACLs disabled, SSE-S3 encryption on.
- Choose storage classes by access pattern; use lifecycle rules to move or expire data automatically.
- Versioning protects against overwrites and deletes but bills every version, so add non-current version expiry.
- Control access with IAM and bucket policies; serve public content through CloudFront rather than a public bucket.

## References

- https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html
- https://docs.aws.amazon.com/AmazonS3/latest/userguide/storage-class-intro.html
- https://docs.aws.amazon.com/AmazonS3/latest/userguide/Versioning.html
- https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html
- https://docs.aws.amazon.com/AmazonS3/latest/userguide/default-encryption-faq.html
- https://docs.aws.amazon.com/AmazonS3/latest/userguide/default-s3-c-encryption-setting-faq.html
- https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-block-public-access.html
- https://docs.aws.amazon.com/AmazonS3/latest/userguide/about-object-ownership.html
- https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucket-policies.html
