# Session 18 – AWS Services: VPC (Networking)

**Author:** Pranay Reddy
**Course:** SST DevOps & Cloud [SWE]
**Session:** 18, Task 2 (AWS Services Research)

All CLI commands in this file are reference commands (not run against a live account).

---

## What is VPC?

Amazon Virtual Private Cloud (VPC) is a logically isolated private network inside an AWS Region. You define its IP address range, split it into subnets, and control routing and firewalls. EC2 instances, RDS databases, load balancers, EKS nodes and Lambda functions (when VPC-attached) all live in a VPC.

- A VPC spans **one Region** and all of its Availability Zones.
- A subnet lives in **exactly one AZ**.
- Every Region has a **default VPC** (`172.31.0.0/16`) with a public subnet in each AZ, convenient for testing. Production workloads use custom VPCs, usually defined in Terraform.
- VPCs themselves are free; NAT gateways, public IPv4 addresses, VPC endpoints (interface type) and data transfer cost money.

---

## CIDR

CIDR (Classless Inter-Domain Routing) notation describes an IP range: `10.0.0.0/16` means the first 16 bits are fixed, leaving 16 bits for hosts (65,536 addresses).

| CIDR | Addresses | Typical use |
| :--- | :--- | :--- |
| `/16` | 65,536 | Whole VPC (largest allowed) |
| `/20` | 4,096 | Large subnet (EKS nodes) |
| `/24` | 256 | Common subnet size |
| `/28` | 16 | Smallest allowed subnet/VPC |

Rules:

- IPv4 VPC CIDR size must be between `/16` and `/28`.
- Use private RFC 1918 ranges: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`.
- Plan ranges so they **do not overlap** with on-prem networks or other VPCs you may peer with later.
- You can add secondary CIDR blocks and an IPv6 block (`/56`) to a VPC.
- AWS reserves **5 addresses in every subnet**: network address, `.1` (VPC router), `.2` (DNS), `.3` (reserved for future use) and the broadcast address. A `/24` therefore has 251 usable IPs.

---

## Subnets

A subnet is a slice of the VPC CIDR placed in one AZ. Whether it is "public" or "private" depends only on its **route table**, not on a setting with that name.

Typical design (two AZs for high availability):

| Subnet | AZ | CIDR | Tier |
| :--- | :--- | :--- | :--- |
| public-a | ap-south-1a | 10.0.1.0/24 | Load balancer, NAT gateway |
| public-b | ap-south-1b | 10.0.2.0/24 | Load balancer, NAT gateway |
| private-app-a | ap-south-1a | 10.0.11.0/24 | EC2 / EKS nodes |
| private-app-b | ap-south-1b | 10.0.12.0/24 | EC2 / EKS nodes |
| private-db-a | ap-south-1a | 10.0.21.0/24 | RDS |
| private-db-b | ap-south-1b | 10.0.22.0/24 | RDS standby |

---

## Route tables

A route table is a set of rules that tells the VPC router where to send traffic based on the destination.

- Every VPC has a **main route table**; you create custom ones and associate subnets explicitly.
- Each subnet is associated with exactly one route table.
- Every table contains the **local route** (VPC CIDR → `local`), which cannot be deleted, so all subnets can reach each other.
- The **most specific** matching route wins (longest prefix match).

Public route table:

| Destination | Target |
| :--- | :--- |
| 10.0.0.0/16 | local |
| 0.0.0.0/0 | igw-0abc (Internet Gateway) |

Private route table (AZ a):

| Destination | Target |
| :--- | :--- |
| 10.0.0.0/16 | local |
| 0.0.0.0/0 | nat-0aaa (NAT gateway) |
| pl-xxxx (S3 prefix list) | vpce-0s3 (gateway endpoint) |

---

## Internet Gateway

An Internet Gateway (IGW) connects a VPC to the internet.

- One IGW per VPC; horizontally scaled and highly available by AWS, with no bandwidth limit and no hourly charge.
- Provides **two-way** connectivity: instances with a public IP can be reached from the internet and can reach it.
- Performs 1:1 translation between an instance's private IP and its public IPv4 / Elastic IP.
- A subnet becomes public when its route table sends `0.0.0.0/0` to the IGW.
- For IPv6-only outbound traffic, an **egress-only internet gateway** is used instead of NAT.

---

## NAT Gateway

A NAT gateway lets resources in **private** subnets start outbound connections (OS updates, external APIs, pulling container images) while preventing inbound connections from the internet.

- **Zonal** NAT gateway (classic): created in a public subnet with an Elastic IP; deploy one per AZ so one AZ failure does not cut off the others.
- **Regional** NAT gateway (newer availability mode): a single NAT gateway for the VPC that expands across AZs automatically and does not need a public subnet.
- Private NAT gateways (no Elastic IP) exist for routing between private networks.
- Charged per hour **and** per GB processed; often one of the biggest networking costs. Use **VPC gateway endpoints** for S3 and DynamoDB (free) so that traffic skips the NAT.

---

## Security Groups

Security groups act at the **network interface (instance) level**. They are stateful and contain only allow rules. A rule can reference another security group, which is the cleanest way to express tiers:

```text
alb-sg :  inbound 443 from 0.0.0.0/0
app-sg :  inbound 8080 from alb-sg
db-sg  :  inbound 5432 from app-sg
```

(See also [02-ec2](../02-ec2/README.md#security-groups).)

---

## Network ACLs

A network ACL (NACL) is an optional firewall at the **subnet** level.

- **Stateless**: return traffic must be allowed explicitly, including ephemeral ports (1024–65535) for responses.
- Supports **allow and deny** rules, evaluated in **rule-number order**, lowest first; first match wins; final `*` rule denies.
- The **default NACL** allows all inbound and outbound traffic. A **new custom NACL** denies everything until rules are added.
- Useful for blocking a specific IP range across a whole subnet.

Security Group vs Network ACL:

| Feature | Security Group | Network ACL |
| :--- | :--- | :--- |
| Level | Network interface (instance) | Subnet |
| State | Stateful | Stateless |
| Rules | Allow only | Allow and deny |
| Evaluation | All rules evaluated together | In order by rule number, first match wins |
| Default | Deny all inbound, allow all outbound | Default NACL allows all |
| Can reference other SGs | Yes | No, CIDR only |

---

## Public vs private subnet

| | Public subnet | Private subnet |
| :--- | :--- | :--- |
| Default route `0.0.0.0/0` | Internet Gateway | NAT gateway (or none) |
| Instances need public IP | Yes, to be reachable | No |
| Reachable from internet | Yes, if SG allows | No |
| Outbound internet | Directly via IGW | Via NAT gateway |
| Typical resources | ALB, NAT gateway, bastion | App servers, EKS nodes, RDS, caches |

Typical two-AZ layout:

```text
                         Internet
                            |
                    [Internet Gateway]
                            |
 VPC 10.0.0.0/16 -----------+-------------------------------------
 |                                                               |
 |   AZ ap-south-1a                    AZ ap-south-1b            |
 |  +-------------------------+      +-------------------------+ |
 |  | Public  10.0.1.0/24     |      | Public  10.0.2.0/24     | |
 |  |  [ALB node] [NAT GW]    |      |  [ALB node] [NAT GW]    | |
 |  +-----------|-------------+      +-----------|-------------+ |
 |              v                                v               |
 |  +-------------------------+      +-------------------------+ |
 |  | Private 10.0.11.0/24    |      | Private 10.0.12.0/24    | |
 |  |  [EC2 app]              |      |  [EC2 app]              | |
 |  +-------------------------+      +-------------------------+ |
 |  +-------------------------+      +-------------------------+ |
 |  | DB      10.0.21.0/24    |      | DB      10.0.22.0/24    | |
 |  |  [RDS primary]  <-sync->|------|  [RDS standby]          | |
 |  +-------------------------+      +-------------------------+ |
 -----------------------------------------------------------------
```

Reference commands:

```bash
aws ec2 describe-vpcs --query 'Vpcs[].[VpcId,CidrBlock,IsDefault]' --output table
aws ec2 describe-subnets --filters Name=vpc-id,Values=vpc-0abc \
  --query 'Subnets[].[SubnetId,AvailabilityZone,CidrBlock,MapPublicIpOnLaunch]' --output table
aws ec2 describe-route-tables --filters Name=vpc-id,Values=vpc-0abc
aws ec2 describe-network-acls --filters Name=vpc-id,Values=vpc-0abc
```

Terraform snippet (one public subnet):

```hcl
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  tags = { Name = "pranay-vpc" }
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id
}

resource "aws_subnet" "public_a" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "ap-south-1a"
  map_public_ip_on_launch = true
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }
}

resource "aws_route_table_association" "public_a" {
  subnet_id      = aws_subnet.public_a.id
  route_table_id = aws_route_table.public.id
}
```

---

## Key takeaways

- A VPC is a Regional private network; subnets are per-AZ slices of its CIDR (`/16` to `/28`, 5 IPs reserved per subnet).
- A subnet is public only because its route table points `0.0.0.0/0` at an Internet Gateway.
- Private subnets reach the internet outbound through a NAT gateway; use gateway endpoints for S3/DynamoDB to save NAT cost.
- Security groups are stateful and per-instance; NACLs are stateless, ordered, per-subnet, and can deny.
- Spread subnets across at least two AZs and plan non-overlapping CIDRs up front.

## References

- https://docs.aws.amazon.com/vpc/latest/userguide/what-is-amazon-vpc.html
- https://docs.aws.amazon.com/vpc/latest/userguide/vpc-cidr-blocks.html
- https://docs.aws.amazon.com/vpc/latest/userguide/subnet-sizing.html
- https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Route_Tables.html
- https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Internet_Gateway.html
- https://docs.aws.amazon.com/vpc/latest/userguide/vpc-nat-gateway.html
- https://docs.aws.amazon.com/vpc/latest/userguide/vpc-network-acls.html
- https://docs.aws.amazon.com/vpc/latest/userguide/infrastructure-security.html
