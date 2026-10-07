# Session 18 – AWS Services: IAM (Governance)

**Author:** Pranay Reddy
**Course:** SST DevOps & Cloud [SWE]
**Session:** 18, Task 2 (AWS Services Research)

All CLI commands in this file are reference commands (not run against a live account).

---

## What is IAM?

AWS Identity and Access Management (IAM) is the service that decides **who** can do **what** on **which** AWS resource. Every API call to AWS (console click, CLI command, SDK call, Terraform apply) is signed with credentials, and IAM evaluates that request against policies before it is allowed or denied.

Key points:

- IAM is a **global** service. Users, groups, roles and policies are not tied to a Region.
- IAM itself has no extra charge.
- Two questions are answered on every request: **authentication** (who are you?) and **authorization** (are you allowed to do this?).
- The **root user** (the email used to create the account) has full access and cannot be restricted by IAM policies. It should be protected with MFA and not used for daily work.

---

## Users

An IAM user is an identity with long-term credentials that belongs to one AWS account.

| Credential | Used for |
| :--- | :--- |
| Password | AWS Management Console sign-in |
| Access key ID + secret access key | CLI, SDK, API calls |
| MFA device | Second factor for console (and optionally API) |

AWS now recommends that **humans** sign in through **IAM Identity Center** (federation, short-lived credentials) instead of individual IAM users with long-term access keys. IAM users still exist and are useful for a few cases, such as a third-party tool that cannot assume a role.

```bash
# Reference commands
aws iam create-user --user-name pranay-dev
aws iam list-users --query 'Users[].UserName'
aws sts get-caller-identity          # "who am I" for the current credentials
```

---

## Groups

A group is a collection of IAM users. Policies attached to the group apply to every user in it.

- A user can be in multiple groups.
- Groups cannot contain other groups (no nesting).
- A group is **not** an identity; it cannot be referenced as a principal in a resource policy and cannot sign requests.

Typical layout: `Admins`, `Developers`, `ReadOnly`, `Billing`.

```bash
aws iam create-group --group-name Developers
aws iam add-user-to-group --group-name Developers --user-name pranay-dev
aws iam attach-group-policy --group-name Developers \
  --policy-arn arn:aws:iam::aws:policy/ReadOnlyAccess
```

---

## Roles

A role is an identity with permissions but **no long-term credentials**. Someone or something *assumes* the role and receives temporary credentials from AWS STS (Security Token Service).

A role has two policies:

1. **Trust policy** – who is allowed to assume the role (a service, another account, a federated user).
2. **Permissions policy** – what the role can do once assumed.

Common role types:

| Role type | Example |
| :--- | :--- |
| Service role | EC2 instance profile that reads from S3; Lambda execution role |
| Cross-account role | CI account deploys into a prod account |
| Federated / OIDC role | GitHub Actions assumes a role via OIDC, no stored keys |
| Service-linked role | Created and managed by a service (e.g. Auto Scaling) |

Trust policy that lets EC2 assume the role:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": { "Service": "ec2.amazonaws.com" },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

---

## Policies

A policy is a JSON document that lists permissions. Each statement has:

| Element | Meaning |
| :--- | :--- |
| `Effect` | `Allow` or `Deny` |
| `Action` | API actions, e.g. `s3:GetObject` |
| `Resource` | ARNs the statement applies to |
| `Condition` | Optional extra checks (IP, MFA, tags, VPC endpoint, time) |
| `Principal` | Only in resource-based and trust policies: who the statement is about |

Policy types:

- **Identity-based** – attached to users, groups, roles.
  - *AWS managed* (e.g. `ReadOnlyAccess`), *customer managed* (you write and version them), *inline* (embedded in one identity).
- **Resource-based** – attached to the resource itself (S3 bucket policy, SQS queue policy, KMS key policy, role trust policy).
- **Permissions boundaries** – the maximum permissions an identity-based policy can grant to a user or role.
- **Service control policies (SCPs) / resource control policies (RCPs)** – AWS Organizations guardrails for whole accounts.
- **Session policies** – passed when assuming a role to narrow that session.

---

## Permissions

How AWS evaluates a request (simplified, single account):

```text
Request arrives
     |
     v
Any explicit Deny in any applicable policy?  --yes-->  DENIED
     |
     no
     v
Allowed by SCP / RCP / permissions boundary (if they exist)?  --no-->  DENIED
     |
     yes
     v
Any Allow in identity-based or resource-based policy?  --no-->  DENIED (implicit deny)
     |
     yes
     v
  ALLOWED
```

Rules to remember:

- Everything starts as **implicit deny**.
- An **explicit Deny always wins** over any Allow.
- Cross-account access needs an Allow on **both** sides (the caller's identity policy and the resource policy or role trust).

---

## Least privilege

Least privilege means granting only the actions and resources needed for the task, and nothing else.

Example: an application only needs to read and write objects under one prefix of one bucket. Instead of `AmazonS3FullAccess`, use:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ListOnlyAppPrefix",
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::pranay-app-data",
      "Condition": {
        "StringLike": { "s3:prefix": ["uploads/*"] }
      }
    },
    {
      "Sid": "ReadWriteAppObjects",
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject"],
      "Resource": "arn:aws:s3:::pranay-app-data/uploads/*"
    }
  ]
}
```

Note that `s3:ListBucket` applies to the bucket ARN, while object actions apply to `bucket/*`. Mixing these up is a common reason a policy "does not work".

Tools that help reach least privilege:

- **IAM Access Analyzer** – finds resources shared outside the account, flags unused access, validates policies, and can generate a policy from CloudTrail activity.
- **Last accessed information** – shows which services a role actually used, so unused permissions can be removed.

---

## IAM best practices

1. Lock away the root user: enable MFA, delete root access keys, use it only for the few tasks that require it.
2. Use **IAM Identity Center** / federation for people, so they get temporary credentials.
3. Use **roles** for workloads (EC2 instance profiles, Lambda execution roles, ECS task roles, OIDC for CI/CD) instead of access keys.
4. Require MFA for human users.
5. Rotate or remove long-term access keys; never commit them to Git.
6. Start from AWS managed policies, then move to **customer managed** least-privilege policies.
7. Use conditions (`aws:SourceIp`, `aws:MultiFactorAuthPresent`, `aws:PrincipalOrgID`) to tighten access.
8. Use permissions boundaries and SCPs to set guardrails in multi-account setups.
9. Review regularly with Access Analyzer and last-accessed data.
10. Turn on **CloudTrail** so every IAM-authorized API call is logged.

---

## Common use cases

- Give a developer team read-only access to production but full access to a dev account.
- Let an EC2 instance read secrets from Secrets Manager without storing keys on the instance.
- Let GitHub Actions deploy with Terraform through an OIDC role (no stored secrets).
- Allow a partner account to read one S3 bucket via a cross-account role.
- Enforce "no one can disable CloudTrail" with an SCP across all accounts.

Terraform example: a role for EC2 with the least-privilege S3 policy above.

```hcl
resource "aws_iam_role" "app" {
  name = "pranay-app-ec2-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "s3_uploads" {
  name   = "s3-uploads-rw"
  role   = aws_iam_role.app.id
  policy = file("${path.module}/s3-uploads-policy.json")
}

resource "aws_iam_instance_profile" "app" {
  name = "pranay-app-profile"
  role = aws_iam_role.app.name
}
```

More reference commands:

```bash
aws iam list-attached-role-policies --role-name pranay-app-ec2-role
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::123456789012:role/pranay-app-ec2-role \
  --action-names s3:GetObject s3:DeleteObject \
  --resource-arns arn:aws:s3:::pranay-app-data/uploads/file.txt
aws accessanalyzer validate-policy --policy-type IDENTITY_POLICY \
  --policy-document file://s3-uploads-policy.json
```

---

## Key takeaways

- IAM is global and free; it authenticates and authorizes every AWS API call.
- Users and groups are for people (prefer Identity Center); roles with temporary credentials are for workloads and cross-account access.
- Policies are JSON; an explicit Deny always overrides an Allow, and the default is implicit deny.
- Least privilege means scoping both actions and resources, then trimming with Access Analyzer.
- Protect the root user with MFA and never use long-term keys where a role will do.

## References

- https://docs.aws.amazon.com/IAM/latest/UserGuide/introduction.html
- https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html
- https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html
- https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles.html
- https://docs.aws.amazon.com/IAM/latest/UserGuide/what-is-access-analyzer.html
- https://docs.aws.amazon.com/singlesignon/latest/userguide/what-is.html
