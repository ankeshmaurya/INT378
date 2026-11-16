# Terraform vs CloudFormation for CloudTask

CloudTask uses Terraform as the primary infrastructure path and CloudFormation as an AWS-only comparison. The CloudFormation template provisions the equivalent foundation: VPC, public subnet, internet gateway, route table, security group, EC2 instance, and encrypted versioned S3 bucket.

## Deploy and delete with AWS CLI

Use the AWS CLI from the repository root. The commands below target `ap-south-1`; change the region if the AMI and key pair are in another region.

```powershell
aws cloudformation validate-template `
  --template-body file://cloudformation/cloudtask.yml `
  --region ap-south-1

aws cloudformation deploy `
  --template-file cloudformation/cloudtask.yml `
  --stack-name cloudtask-comparison `
  --region ap-south-1 `
  --capabilities CAPABILITY_NAMED_IAM `
  --parameter-overrides `
    ProjectName=cloudtask `
    AmiId=ami-your-ubuntu-ami-id `
    KeyName=cloudtask-ap-south-1 `
    SshCidr=YOUR_PUBLIC_IP/32 `
    MonitoringCidr=YOUR_MONITORING_CIDR/32 `
    AppPort=5000

aws cloudformation describe-stacks `
  --stack-name cloudtask-comparison `
  --region ap-south-1 `
  --query "Stacks[0].Outputs"
```

Delete the stack when finished to avoid EC2 and networking charges:

```powershell
aws cloudformation delete-stack `
  --stack-name cloudtask-comparison `
  --region ap-south-1

aws cloudformation wait stack-delete-complete `
  --stack-name cloudtask-comparison `
  --region ap-south-1
```

The S3 bucket uses `DeletionPolicy: Retain`, so remove its contents and delete it separately if it is no longer needed.

## Comparison

### Syntax

Terraform uses HCL with separate resource blocks and references such as `aws_vpc.main.id`. CloudFormation uses YAML resource objects, intrinsic functions such as `!Ref` and `!GetAtt`, and AWS-specific resource property names. Terraform felt more compact for composing dependencies; CloudFormation was more verbose but made the AWS resource model explicit.

### State handling

Terraform keeps a state file that maps configuration resources to real infrastructure. That makes drift and dependency planning clear, but the state must be protected and shared safely in a team backend. CloudFormation stores stack state inside AWS and manages the stack as one AWS-owned unit, so there is no separate state file to secure. The tradeoff is less direct control over state inspection and more reliance on stack events during troubleshooting.

### Multi-cloud support

Terraform can use AWS, Azure, GCP, and many other providers with the same workflow. CloudFormation is designed for AWS resources and AWS service integrations. For CloudTask, Terraform is the better primary path because the project is explicitly about portable infrastructure concepts, while CloudFormation is useful as an AWS-native comparison.

### Learning curve

Terraform required learning HCL, provider versions, state, variables, and plan/apply lifecycle. CloudFormation required learning intrinsic functions, parameter types, resource-specific YAML properties, and stack update behavior. CloudFormation was initially familiar because it stays close to AWS documentation; Terraform became easier to maintain once the resource graph and reusable variables were established.

### My CloudTask experience

Building the same CloudTask VPC, subnet, route, security group, EC2 instance, and S3 bucket in both tools made the difference practical. Terraform made it easier to reuse variables such as the SSH CIDR, monitoring CIDR, instance type, and application port, and `terraform validate` gave fast feedback before deployment. CloudFormation made the AWS dependency structure and stack outputs straightforward, but a single incorrect property name, such as the S3 versioning property, required an AWS-specific lint check. I would keep Terraform as the maintainable primary implementation and use the CloudFormation template to demonstrate AWS-native provisioning and stack lifecycle management.
