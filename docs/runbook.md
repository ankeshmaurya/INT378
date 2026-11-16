# Verification runbook

- Application: `python -m pytest`
- Security scan: `bandit -r app lambda -ll`
- Image scan: `trivy image --severity HIGH,CRITICAL cloudtask:local`
- Compose smoke check: `docker compose --env-file .env -f docker/docker-compose.yml ps`
- Terraform syntax: `terraform -chdir=terraform fmt -check` and `terraform -chdir=terraform validate`
- Health: `curl http://localhost:5000/health`
- Metrics: `curl http://localhost:5000/metrics`

For AWS spend, review Cost Explorer and configure the Terraform budget notification email. Keep the SSH CIDR as a narrow `/32` whenever possible.
