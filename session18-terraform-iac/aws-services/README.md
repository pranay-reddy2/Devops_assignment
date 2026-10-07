# Session 18 – AWS Services Research

**Author:** Pranay Reddy
**Course:** SST DevOps & Cloud [SWE]
**Session:** 18, Task 2 (AWS Services Research)

Research notes on the core AWS services that the Terraform work in this session provisions. Each sub-folder covers one service area with concepts, tables, sample JSON policies, reference AWS CLI commands (not run) and a short Terraform snippet.

---

## Contents

| # | Service | Category | Summary |
| :--- | :--- | :--- | :--- |
| 01 | [IAM](01-iam/README.md) | Governance | Users, groups, roles and JSON policies that control who can call which AWS API; least privilege and best practices. |
| 02 | [EC2](02-ec2/README.md) | Compute | Virtual servers: AMIs, instance types, key pairs, security groups, EBS, IP addressing and the instance lifecycle. |
| 03 | [S3](03-s3/README.md) | Storage | Object storage: buckets, objects, storage classes, versioning, lifecycle rules, encryption and bucket policies. |
| 04 | [VPC](04-vpc/README.md) | Networking | Private network design: CIDR, subnets, route tables, Internet/NAT gateways, security groups vs NACLs. |
| 05 | [DynamoDB & RDS](05-dynamodb-rds/README.md) | Databases | Serverless NoSQL (keys, items, capacity modes) vs managed SQL (engines, Multi-AZ, read replicas, backups). |

---

## How the services fit together

A typical three-tier web application in one Region:

```text
   Users (browser / mobile)
            |
            v  HTTPS
 +----------------------------------------------------------------+
 | VPC 10.0.0.0/16   (networking boundary)                        |
 |                                                                |
 |  Public subnets      [Internet Gateway] -> [Load Balancer]     |
 |                                      [NAT Gateway]             |
 |                              |              ^                  |
 |  Private app subnets         v              | outbound only    |
 |                     [EC2 instances / Auto Scaling group]       |
 |                       |  (IAM role via instance profile)       |
 |            +----------+-------------+-----------------+        |
 |            |                        |                 |        |
 |  Private DB subnets                 |                 |        |
 |     [RDS PostgreSQL]                |                 |        |
 |     primary + Multi-AZ standby      |                 |        |
 +-------------------------------------|-----------------|--------+
                                       | VPC endpoints   |
                                       v                 v
                                 [Amazon S3]       [DynamoDB]
                              uploads, assets,    sessions, carts,
                              logs, TF state      fast key lookups

  IAM wraps everything: who may deploy (users/roles, OIDC for CI/CD),
  what the EC2 role may touch (S3 prefix, DynamoDB table), and
  resource policies on the S3 bucket.
```

- **IAM** decides who and what can call AWS APIs (people, CI pipelines, EC2 instance roles).
- **VPC** provides the private network, subnets and firewalls everything else runs in.
- **EC2** runs the application code in private subnets behind a load balancer.
- **RDS** stores relational data (users, orders) in private DB subnets with Multi-AZ failover.
- **DynamoDB** stores high-volume key-value data (sessions, carts) with no servers to manage.
- **S3** stores files, static assets, logs, backups and the Terraform remote state.
