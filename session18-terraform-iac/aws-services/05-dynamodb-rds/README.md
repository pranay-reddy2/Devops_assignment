# Session 18 – AWS Services: DynamoDB & RDS (Databases)

**Author:** Pranay Reddy
**Course:** SST DevOps & Cloud [SWE]
**Session:** 18, Task 2 (AWS Services Research)

All CLI commands in this file are reference commands (not run against a live account).

---

# Part 1: Amazon DynamoDB

## NoSQL

Amazon DynamoDB is a fully managed, serverless **NoSQL key-value and document database**. There are no servers, OS patches or storage volumes to manage.

- Single-digit millisecond latency at any scale.
- Data is replicated across three AZs in a Region automatically; **encryption at rest is always on**.
- No fixed schema: only the primary key is defined up front; every other attribute can differ between items.
- No joins. Data is modelled around **access patterns** (the queries the app will run), not around normalized tables.
- Capacity modes:

| Mode | Billing | Best for |
| :--- | :--- | :--- |
| **On-demand** (default and recommended) | Per read/write request | New, spiky or unpredictable traffic; idle tables cost nothing for throughput |
| **Provisioned** | Per RCU/WCU per hour, optional auto scaling | Steady, predictable traffic where you can forecast capacity |

Reads are **eventually consistent** by default; you can request **strongly consistent** reads for a single Region table.

## Tables

A table is a collection of items. You define:

- Table name and **primary key** (partition key, optionally plus sort key).
- Capacity mode.
- Optional **secondary indexes**: Global Secondary Index (GSI, different partition/sort key, can be added any time) and Local Secondary Index (LSI, same partition key, different sort key, must be created with the table).
- Optional features: TTL (auto-delete expired items), DynamoDB Streams (change feed for Lambda), Point-in-Time Recovery, Global Tables (multi-Region, active-active replication).

## Items

An item is one record in a table, similar to a row. Each item is identified by its primary key and can be up to **400 KB** in size (including attribute names).

```json
{
  "UserId":   { "S": "u#1001" },
  "OrderId":  { "S": "2026-10-07#A17" },
  "Total":    { "N": "1499" },
  "Status":   { "S": "SHIPPED" },
  "Items":    { "L": [ { "S": "keyboard" }, { "S": "mouse" } ] }
}
```

## Attributes

An attribute is a name-value pair inside an item, similar to a column but not fixed across items.

| Category | Types (API code) |
| :--- | :--- |
| Scalar | String `S`, Number `N`, Binary `B`, Boolean `BOOL`, Null `NULL` |
| Document | Map `M`, List `L` (can be nested) |
| Set | String set `SS`, Number set `NS`, Binary set `BS` |

## Partition key

The partition key (hash key) is required. DynamoDB hashes its value to decide which internal partition stores the item.

- With a partition-key-only table, the partition key must be **unique** per item.
- Choose a **high-cardinality** key (e.g. `UserId`, `DeviceId`) so traffic spreads evenly. A low-cardinality key such as `Status` creates "hot partitions" and throttling.
- `GetItem` and `Query` need the partition key value; filtering by other attributes without a key or index requires a `Scan` (reads the whole table, slow and expensive).

## Sort key

The sort key (range key) is optional. With it, the **primary key = partition key + sort key**, and multiple items can share the same partition key.

- Items with the same partition key are stored together, ordered by sort key.
- Enables range queries: `begins_with`, `between`, `<`, `>`.
- Example: partition key `UserId`, sort key `OrderId` beginning with a date, so "all orders of user u#1001 in October 2026" is one `Query`.

```bash
aws dynamodb create-table --table-name Orders \
  --attribute-definitions AttributeName=UserId,AttributeType=S AttributeName=OrderId,AttributeType=S \
  --key-schema AttributeName=UserId,KeyType=HASH AttributeName=OrderId,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST

aws dynamodb put-item --table-name Orders --item file://order.json

aws dynamodb query --table-name Orders \
  --key-condition-expression "UserId = :u AND begins_with(OrderId, :m)" \
  --expression-attribute-values '{":u":{"S":"u#1001"},":m":{"S":"2026-10"}}'
```

```hcl
resource "aws_dynamodb_table" "orders" {
  name         = "Orders"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "UserId"
  range_key    = "OrderId"

  attribute {
    name = "UserId"
    type = "S"
  }
  attribute {
    name = "OrderId"
    type = "S"
  }

  point_in_time_recovery { enabled = true }
}
```

## DynamoDB use cases

- User sessions, shopping carts, user profiles.
- Leaderboards, counters, IoT device data with known access patterns.
- Serverless backends (API Gateway + Lambda + DynamoDB).
- Metadata store for files kept in S3.
- Terraform state locking (older setups; Terraform now supports S3-native locking).

---

# Part 2: Amazon RDS

## Relational database

Amazon Relational Database Service (RDS) runs managed relational (SQL) databases. AWS handles provisioning, OS and engine patching, backups, monitoring and failover; you still design schemas, write SQL and choose instance sizes.

Relational databases store data in tables with fixed columns, enforce relationships with foreign keys, support joins and **ACID transactions**, and are queried with SQL.

## Supported engines

| Engine | Default port | Notes |
| :--- | :--- | :--- |
| Amazon Aurora MySQL-Compatible | 3306 | AWS-built, cluster storage across 3 AZs |
| Amazon Aurora PostgreSQL-Compatible | 5432 | Also offers Aurora Serverless v2 |
| MySQL | 3306 | Community edition |
| MariaDB | 3306 | Community edition |
| PostgreSQL | 5432 | Community edition |
| Oracle | 1521 | License included or BYOL |
| Microsoft SQL Server | 1433 | Express, Web, Standard, Enterprise editions |
| IBM Db2 | 50000 | Standard and Advanced editions |

## DB instances

A DB instance is an isolated database environment with its own compute and storage.

- **Instance class**: e.g. `db.t4g.micro` (burstable), `db.m7g.large` (general), `db.r7g.xlarge` (memory optimized).
- **Storage**: General Purpose SSD (`gp3`, `gp2`) or Provisioned IOPS SSD (`io1`, `io2`); storage autoscaling can grow it automatically.
- **Endpoint**: a DNS name such as `mydb.abc123xyz.ap-south-1.rds.amazonaws.com`; applications connect to the endpoint, never to an IP.
- **DB subnet group**: the set of private subnets (at least two AZs) where RDS can place the instance.
- **Parameter groups** hold engine settings; **option groups** add engine features (Oracle, SQL Server).

```bash
aws rds describe-db-instances \
  --query 'DBInstances[].[DBInstanceIdentifier,Engine,DBInstanceClass,DBInstanceStatus,MultiAZ,Endpoint.Address]' \
  --output table
```

## Security

- **Network**: place instances in private subnets, keep `PubliclyAccessible = false`, and allow the DB port only from the application security group.
- **Encryption at rest** with AWS KMS; it must be enabled at creation (an unencrypted DB is encrypted by restoring from an encrypted snapshot copy). Snapshots, replicas and backups inherit encryption.
- **Encryption in transit** with SSL/TLS; engines can be configured to require it.
- **Authentication**: master user password managed in **AWS Secrets Manager** (with rotation), **IAM database authentication** for MySQL, MariaDB and PostgreSQL, and Kerberos/Active Directory for some engines.
- **IAM** controls who can manage the instance (create, modify, delete), separate from database users.
- Audit with CloudTrail (API calls) and engine logs exported to CloudWatch Logs.

## Backups

| Type | How | Retention |
| :--- | :--- | :--- |
| Automated backups | Daily snapshot during the backup window plus transaction logs | 0–35 days (0 disables them) |
| Point-in-time restore | Restore to any second within the retention period, typically up to the last 5 minutes | Same as automated backups |
| Manual snapshots | Taken on demand | Kept until you delete them, survive DB deletion |

A restore always creates a **new** DB instance with a new endpoint. Snapshots can be copied to other Regions or accounts. AWS Backup can manage RDS backups centrally.

## Multi-AZ

Multi-AZ is for **high availability**, not for scaling reads.

| Deployment | Layout | Standby readable? | Failover |
| :--- | :--- | :--- | :--- |
| Multi-AZ DB instance | Primary + 1 standby in another AZ, synchronous replication | No | Automatic; DNS endpoint moves to standby, typically 1–2 minutes |
| Multi-AZ DB cluster (MySQL, PostgreSQL) | Writer + 2 readable standbys in 3 AZs | Yes (reader endpoint) | Automatic, typically under 35 seconds |

Failover is triggered by events such as AZ outage, primary host failure, or a reboot with failover. Patching is applied to the standby first to reduce downtime.

## Read replicas

Read replicas are for **read scaling** (and can help with disaster recovery).

- **Asynchronous** replication from the source, so replicas can lag slightly.
- Up to **15** read replicas per source for MySQL, MariaDB and PostgreSQL; fewer for Oracle, SQL Server and Db2.
- Each replica has its own endpoint; the application sends read-only queries (reports, dashboards) there.
- Can be in the same Region or **cross-Region** (most engines).
- A replica can be **promoted** to a standalone DB (manual, breaks replication).
- Requires automated backups on the source.

```bash
aws rds create-db-instance-read-replica \
  --db-instance-identifier pranay-db-replica-1 \
  --source-db-instance-identifier pranay-db
```

Terraform snippet:

```hcl
resource "aws_db_instance" "app" {
  identifier                  = "pranay-db"
  engine                      = "postgres"
  instance_class              = "db.t4g.micro"
  allocated_storage           = 20
  storage_type                = "gp3"
  storage_encrypted           = true
  username                    = "appadmin"
  manage_master_user_password = true          # password stored in Secrets Manager
  db_subnet_group_name        = aws_db_subnet_group.private.name
  vpc_security_group_ids      = [aws_security_group.db.id]
  multi_az                    = true
  backup_retention_period     = 7
  publicly_accessible         = false
  deletion_protection         = true
}
```

## RDS use cases

- Backend database for web apps and APIs (users, orders, payments) that need transactions and joins.
- Lift-and-shift of existing MySQL, PostgreSQL, Oracle, SQL Server or Db2 databases.
- ERP, CRM and reporting systems with complex SQL.
- WordPress/CMS databases.

---

## DynamoDB vs RDS

| Aspect | DynamoDB | RDS |
| :--- | :--- | :--- |
| Data model | NoSQL key-value / document | Relational tables, SQL |
| Schema | Flexible, only key defined | Fixed schema, migrations needed |
| Queries | By key/index; no joins | Full SQL, joins, aggregations |
| Scaling | Automatic, horizontal, serverless | Vertical (instance size) plus read replicas |
| Servers to choose | None | Instance class, storage, AZ layout |
| Pricing | Per request or provisioned capacity, plus storage | Per instance-hour plus storage and I/O |
| Transactions | Supported (`TransactWriteItems`), limited scope | Full ACID |
| Best for | Known access patterns, massive scale, low latency | Complex queries, relational data, existing SQL apps |

---

## Key takeaways

- DynamoDB is serverless NoSQL: design the partition key (and sort key) around access patterns, and prefer on-demand capacity unless traffic is predictable.
- Items are up to 400 KB; avoid Scans and hot partitions by choosing high-cardinality keys and adding GSIs.
- RDS runs managed SQL engines (Aurora MySQL/PostgreSQL, MySQL, MariaDB, PostgreSQL, Oracle, SQL Server, Db2) inside your VPC.
- Multi-AZ is for availability (automatic failover); read replicas are for read scaling (asynchronous).
- Keep RDS private, encrypted, with Secrets Manager credentials and automated backups enabled.

## References

- https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Introduction.html
- https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.CoreComponents.html
- https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/capacity-mode.html
- https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-partition-key-design.html
- https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Welcome.html
- https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.MultiAZ.html
- https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_ReadRepl.html
- https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_WorkingWithAutomatedBackups.html
- https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/UsingWithRDS.html
