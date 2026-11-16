# CloudTask cost optimization

CloudTask provisions a monthly AWS Budget and sends email notifications when actual monthly cost exceeds 50%, 80%, and 100% of the configured limit. Set `monthly_budget_limit` and `budget_email` in `terraform.tfvars` before applying.

```powershell
cd terraform
terraform plan -var-file=terraform.tfvars
terraform apply -var-file=terraform.tfvars
```

Budget notifications are an early warning, not a hard spending cap. AWS Budget alerts do not automatically stop resources.

## Use Cost Explorer

1. Open the AWS Console in the billing account and select **Cost Explorer**.
2. Set the date range to the last 30 or 60 days, then choose monthly granularity.
3. Start with **Group by: Service** to identify EC2, EBS, S3, data transfer, and other large contributors.
4. Filter by **Region: Asia Pacific (Mumbai)** and by project/environment tags when available.
5. Change **Group by** to **Usage type** to find public IPv4, EBS volume, snapshot, NAT, data-transfer, and request charges.
6. Compare the current month with the previous month and inspect daily spikes.
7. For EC2 candidates, open CloudWatch metrics and compare CPU, network, memory, and disk behavior with the instance size and workload.
8. Check **Cost and Usage Reports** or the Cost Explorer CSV export when a service total needs deeper investigation.

## Optimization checklist

- [ ] Stop the EC2 instance when a demo or presentation is finished.
- [ ] Run `terraform destroy -var-file=terraform.tfvars` after temporary demonstrations.
- [ ] Confirm the versioned S3 `backups/` lifecycle rule expires current objects after 365 days and noncurrent versions after 90 days.
- [ ] Remove obsolete S3 objects and delete old versions when retention requirements allow it.
- [ ] Right-size EC2 after reviewing CloudWatch CPU, memory, network, and disk metrics; use `t2.micro` or `t3.micro` only when the measured workload supports it.
- [ ] Check for unattached EBS volumes and snapshots.
- [ ] Release unused Elastic IP addresses and remove idle load balancers or NAT gateways.
- [ ] Review data-transfer charges before exposing monitoring ports or moving large backups.
- [ ] Keep Grafana, Prometheus, and Node Exporter restricted to `monitoring_cidr`; this is both a security and cost-control measure.
- [ ] Recheck Cost Explorer after each infrastructure change and before the next demo.

## Stop or destroy demos

Stopping EC2 preserves its EBS volume and public configuration but continues storage charges. For a short pause:

```powershell
aws ec2 stop-instances --instance-ids INSTANCE_ID --region ap-south-1
```

For a temporary Terraform environment that is no longer needed, destroy it:

```powershell
terraform -chdir=terraform destroy -var-file=terraform.tfvars
```

The S3 bucket is configured not to be force-destroyed. Empty it only after confirming backups and static assets are no longer needed, then destroy the Terraform stack.
