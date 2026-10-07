# Session 18 – AWS Services: EC2 (Compute)

**Author:** Pranay Reddy
**Course:** SST DevOps & Cloud [SWE]
**Session:** 18, Task 2 (AWS Services Research)

All CLI commands in this file are reference commands (not run against a live account).

---

## What is EC2?

Amazon Elastic Compute Cloud (EC2) provides virtual servers ("instances") in AWS data centers. You choose the operating system image, CPU/memory size, storage, network placement and firewall rules, and pay for the time the instance runs (per second for Linux, with a 60-second minimum).

EC2 is a **Regional** service, and each instance runs in one **Availability Zone (AZ)** inside a **subnet** of a VPC.

Pricing options:

| Option | When to use |
| :--- | :--- |
| On-Demand | Default, no commitment, short or unpredictable workloads |
| Savings Plans / Reserved Instances | Steady usage, 1 or 3 year commitment for a lower rate |
| Spot Instances | Spare capacity at a large discount; can be interrupted with a 2-minute notice |
| Dedicated Hosts / Instances | Licensing or compliance needs physical isolation |

---

## AMI

An Amazon Machine Image (AMI) is the template used to launch an instance. It contains:

- A root volume snapshot (OS + preinstalled software).
- Launch permissions (private, shared with accounts, or public).
- Block device mappings (which volumes to attach).

AMIs are Region-specific; copy an AMI to use it in another Region. Sources: AWS-provided (Amazon Linux 2023, Ubuntu, Windows Server), AWS Marketplace, community AMIs, or your own "golden" images built with tools like Packer or EC2 Image Builder.

```bash
# Latest Amazon Linux 2023 AMI ID via the public SSM parameter
aws ssm get-parameter \
  --name /aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64 \
  --query Parameter.Value --output text
```

---

## Instance types

An instance type name such as `m7g.large` reads as: family `m`, generation `7`, attribute `g` (Graviton/Arm), size `large`.

| Family | Optimized for | Example types | Typical workload |
| :--- | :--- | :--- | :--- |
| General purpose | Balanced CPU/memory | `t3`, `t4g`, `m7i`, `m7g` | Web servers, small apps, dev/test |
| Compute optimized | High CPU | `c7i`, `c7g` | Batch, CI builds, gaming servers |
| Memory optimized | High RAM | `r7i`, `r7g`, `x2idn` | In-memory caches, large databases |
| Storage optimized | Fast local NVMe disks | `i4i`, `d3` | NoSQL, data warehousing |
| Accelerated computing | GPUs / ML chips | `p5`, `g6`, `inf2`, `trn1` | ML training/inference, graphics |

Common attribute letters: `g` = AWS Graviton (Arm), `i` = Intel, `a` = AMD, `d` = local NVMe instance store, `n` = enhanced networking.

`t` types are **burstable**: they earn CPU credits while idle and spend them under load. In `unlimited` mode (the default for T3/T4g) sustained bursting can add charges.

---

## Key pairs

A key pair is used for SSH access to Linux instances (and for decrypting the Windows administrator password).

- AWS stores the **public** key; you download the **private** key once (`.pem`).
- Supported types: RSA and ED25519.
- The public key is placed in `~/.ssh/authorized_keys` on first boot.

```bash
aws ec2 create-key-pair --key-name pranay-key --key-type ed25519 \
  --query KeyMaterial --output text > pranay-key.pem
chmod 400 pranay-key.pem
ssh -i pranay-key.pem ec2-user@<public-ip>
```

Modern alternative: **Systems Manager Session Manager** or **EC2 Instance Connect**, which avoid opening port 22 and managing long-lived keys.

---

## Security Groups

A security group (SG) is a virtual, **stateful** firewall attached to an instance's network interface.

- Only **allow** rules; anything not allowed is denied.
- Stateful: if inbound traffic is allowed, the response is automatically allowed out.
- A rule source can be a CIDR or **another security group** (e.g. "allow 5432 only from the app SG").
- Default SG for a new group: no inbound rules, all outbound allowed.

Example web server SG:

| Direction | Protocol | Port | Source/Destination | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| Inbound | TCP | 443 | 0.0.0.0/0 | HTTPS from internet |
| Inbound | TCP | 22 | 203.0.113.10/32 | SSH from my IP only |
| Outbound | All | All | 0.0.0.0/0 | Updates, API calls |

---

## EBS

Elastic Block Store (EBS) provides network-attached block volumes for EC2. A volume lives in one AZ and attaches to instances in that same AZ.

| Volume type | Kind | Notes |
| :--- | :--- | :--- |
| `gp3` | General purpose SSD | Default choice. Baseline 3,000 IOPS and 125 MiB/s included regardless of size; can provision up to 80,000 IOPS and 2,000 MiB/s |
| `gp2` | General purpose SSD (older) | IOPS scale with size (3 IOPS/GiB), burst credits |
| `io2` Block Express | Provisioned IOPS SSD | Highest performance and durability for critical databases |
| `st1` | Throughput HDD | Big sequential reads (logs, big data) |
| `sc1` | Cold HDD | Lowest cost, infrequent access |

Other EBS facts:

- **Snapshots** are incremental backups stored in S3 (managed by AWS); used to create AMIs and to copy data across AZs/Regions.
- Volumes can be encrypted with KMS; you can turn on **EBS encryption by default** per Region.
- Volume size, type and IOPS can be changed online (Elastic Volumes).
- **Instance store** is different: local disks physically attached to the host, very fast, but data is lost on stop/terminate.

---

## Public vs private IP

| Address | Scope | Behaviour |
| :--- | :--- | :--- |
| Private IPv4 | Inside the VPC | Assigned from the subnet CIDR; stays with the instance until it is terminated |
| Public IPv4 (auto-assigned) | Internet | Assigned from AWS's pool if the subnet/launch enables it; **released on stop**, a new one is given on start |
| Elastic IP | Internet | Static public IPv4 you allocate to your account and associate with an instance or ENI |
| IPv6 | Internet (globally unique) | Assigned from the VPC's IPv6 range; reachable if routes and SGs allow |

Notes:

- Since February 2024 AWS charges for **all public IPv4 addresses**, including auto-assigned ones and Elastic IPs, whether in use or idle.
- The instance OS only sees its private IP; the public IP is mapped by the Internet Gateway (1:1 NAT).
- Instances in private subnets have no public IP and reach the internet through a NAT gateway.

---

## Instance lifecycle

```text
          launch
            |
            v
        [pending] -----> [running] ----reboot----> [rebooting] --> [running]
                          |     ^
                     stop |     | start
                          v     |
                      [stopping] --> [stopped]
                          |
            (hibernate also goes stopping -> stopped, RAM saved to EBS root)
                          |
     terminate (from running or stopped)
                          v
                  [shutting-down] --> [terminated]
```

| State | Billed for compute? | Notes |
| :--- | :--- | :--- |
| pending | No | Booting |
| running | Yes | Normal operation |
| stopping / stopped | No (EBS still billed) | Public IPv4 released; instance may move to new host |
| hibernated (stopped) | No (EBS still billed) | Memory saved to encrypted EBS root volume |
| terminated | No | Root EBS deleted by default (`DeleteOnTermination=true`) |

Use **termination protection** for important instances.

**Instance metadata (IMDS):** an instance can read its own metadata and role credentials at `http://169.254.169.254`. Use **IMDSv2** (session-token based) by setting `HttpTokens=required`; Amazon Linux 2023 AMIs default to IMDSv2-only, and an account-level default can enforce it for new launches.

---

## Common use cases

- Hosting web/application servers behind an Application Load Balancer with an **Auto Scaling group**.
- Self-managed databases or software that needs OS-level control.
- Jenkins/GitHub Actions self-hosted runners and build agents.
- Batch processing and HPC using Spot Instances.
- GPU instances for ML training and inference.
- Bastion hosts (now often replaced by Session Manager).

Reference commands:

```bash
aws ec2 describe-instances \
  --filters "Name=instance-state-name,Values=running" \
  --query 'Reservations[].Instances[].[InstanceId,InstanceType,PrivateIpAddress,PublicIpAddress]' \
  --output table

aws ec2 run-instances --image-id ami-0123456789abcdef0 --instance-type t3.micro \
  --key-name pranay-key --subnet-id subnet-0abc --security-group-ids sg-0abc \
  --metadata-options HttpTokens=required \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=pranay-web}]'

aws ec2 stop-instances --instance-ids i-0123456789abcdef0
```

Terraform snippet:

```hcl
resource "aws_instance" "web" {
  ami                    = data.aws_ssm_parameter.al2023.value
  instance_type          = "t3.micro"
  subnet_id              = aws_subnet.public_a.id
  vpc_security_group_ids = [aws_security_group.web.id]
  iam_instance_profile   = aws_iam_instance_profile.app.name

  metadata_options {
    http_tokens = "required"   # IMDSv2 only
  }

  root_block_device {
    volume_type = "gp3"
    volume_size = 20
    encrypted   = true
  }

  tags = { Name = "pranay-web" }
}
```

---

## Key takeaways

- EC2 = virtual servers launched from an AMI, sized by instance type, placed in a subnet in one AZ.
- Security groups are stateful allow-only firewalls at the instance (ENI) level.
- Use gp3 EBS by default; EBS persists across stop, instance store does not.
- Auto-assigned public IPs change on stop/start and all public IPv4 addresses are billed; use Elastic IPs or a load balancer for stable endpoints.
- Require IMDSv2 and give instances IAM roles instead of storing access keys.

## References

- https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/concepts.html
- https://docs.aws.amazon.com/ec2/latest/instancetypes/instance-types.html
- https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-lifecycle.html
- https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/configuring-instance-metadata-service.html
- https://docs.aws.amazon.com/ebs/latest/userguide/ebs-volume-types.html
- https://docs.aws.amazon.com/vpc/latest/userguide/vpc-security-groups.html
- https://aws.amazon.com/blogs/aws/new-aws-public-ipv4-address-charge-public-ip-insights/
