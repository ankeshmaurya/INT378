# CloudTask demo and viva screenshot checklist

Capture screenshots at a readable zoom with the project name, relevant URL or AWS region visible where useful. Do not expose passwords, private keys, access tokens, session cookies, full webhook secrets, or unredacted account identifiers. Add a short caption and figure number to every image.

## 1. Application screens

- [ ] **Login screen:** CloudTask sign-in page with the product name visible.
- [ ] **Registration screen:** account creation form.
- [ ] **Empty task dashboard:** authenticated dashboard before tasks are added.
- [ ] **Add task form:** title and description entered before submission.
- [ ] **Task list:** multiple tasks visible with open and completed states.
- [ ] **Edit task:** edited title/description visible after saving.
- [ ] **Completed task:** completed status, visual state, and reopen control.
- [ ] **Delete result:** task list after deletion with the deleted task absent.
- [ ] **Statistics dashboard:** completed count, pending count, and completion percentage returned by Lambda.
- [ ] **Health endpoint:** browser or terminal output showing `/health` returns HTTP 200 and `status: ok`.
- [ ] **Metrics endpoint:** `/metrics` output showing the Flask Prometheus counter.

Suggested captions: “CloudTask task lifecycle” and “Per-user serverless task statistics.”

## 2. Jenkins and DevSecOps pipeline

- [ ] **Jenkins job configuration:** Pipeline script from SCM pointing to the root `Jenkinsfile`.
- [ ] **Jenkins credentials list:** visible credential IDs `dockerhub-creds` and `ec2-ssh-key`; hide values.
- [ ] **Passing pipeline overview:** all stages green from Checkout through Deploy to EC2.
- [ ] **Passing PyTest stage:** console output showing the passing test count and coverage/JUnit publication.
- [ ] **Code Security Scan stage:** Bandit stage passed and `bandit-report.json` archived.
- [ ] **Docker Build stage:** successful image tags including the Jenkins build number and `latest`.
- [ ] **Trivy passing stage:** scan completed with no HIGH or CRITICAL findings.
- [ ] **Deploy to EC2 stage:** successful remote health check and deployment message.
- [ ] **Archived reports:** Jenkins build artifacts showing `coverage.xml`, `test-results.xml`, `bandit-report.json`, `trivy-report.json`, and `secrets-report.txt`.
- [ ] **Deliberate Trivy failure:** a failed pipeline after temporarily using an outdated vulnerable base image such as `python:3.9-slim-buster`; Docker Hub Push and Deploy stages must be skipped.
- [ ] **Failure console output:** Trivy HIGH/CRITICAL finding and the clear Jenkins failure message.

Restore the supported base image after the demonstration and do not use the failed image for deployment.

## 3. Container registry and runtime

- [ ] **Docker Hub repository:** repository page showing the CloudTask image.
- [ ] **Build-number tag:** image tag matching the Jenkins build number.
- [ ] **Latest tag:** `latest` tag updated by the successful pipeline.
- [ ] **EC2 Compose status:** `docker compose ps` showing app, PostgreSQL, Prometheus, Node Exporter, and Grafana running.
- [ ] **EC2 application endpoint:** browser showing CloudTask at the EC2 public IP.
- [ ] **Version verification:** `/health` response showing the `X-CloudTask-Version` header with the deployed image tag.
- [ ] **Build metadata:** `/version` response showing the expected build number, commit hash, and UTC build time.
- [ ] **Application footer:** CloudTask page showing the matching `build #N` text.

## 4. Terraform infrastructure

- [ ] **Terraform init:** successful provider initialization, including AWS and archive providers.
- [ ] **Terraform validate:** “Success! The configuration is valid.”
- [ ] **Terraform plan:** reviewed resource plan before apply.
- [ ] **Terraform apply output:** successful apply summary and created resources.
- [ ] **Terraform outputs:** EC2 public IP, S3 bucket name, and statistics API URL.
- [ ] **VPC:** AWS VPC console showing the CloudTask VPC CIDR.
- [ ] **Public subnet and route table:** subnet, internet gateway, and default route visible.
- [ ] **Security group:** inbound rules showing SSH restricted to the administrator CIDR, HTTP/app ports, and monitoring ports restricted to `monitoring_cidr`.
- [ ] **EC2 instance:** running Ubuntu instance in `ap-south-1` with the CloudTask name and public IP.
- [ ] **S3 bucket:** versioning, AES256 encryption, and public access block enabled.
- [ ] **S3 lifecycle:** `backups/` retention rule showing current and noncurrent version expiration.

## 5. Grafana and monitoring

- [ ] **Grafana login:** Grafana login page at `http://EC2_PUBLIC_IP:3000`; hide the password.
- [ ] **Grafana provisioned datasource:** Prometheus datasource visible and healthy.
- [ ] **Grafana dashboard:** `CloudTask EC2 Overview` showing CPU, memory, disk, network, and HTTP request panels.
- [ ] **Prometheus targets:** targets page showing `node-exporter` and `cloudtask` as UP.
- [ ] **Prometheus alert rules:** rules page showing CPU, memory, disk, and high-5xx error-rate alert rules.
- [ ] **Node Exporter metrics:** Prometheus query or target output proving host metrics are being scraped.
- [ ] **Grafana alert demonstration:** optional controlled load or query showing a threshold panel response without harming the demo instance.

## 6. Lambda and API Gateway

- [ ] **Terraform Lambda output:** `stats_api_url` output visible with the `ap-south-1` endpoint.
- [ ] **API Gateway route:** AWS console showing the HTTP API and `POST /stats` route.
- [ ] **Lambda function:** Lambda console showing `cloudtask-dev-stats` and Python 3.11 runtime.
- [ ] **Lambda test event:** AWS Lambda test using `[`"completed`",`"pending`",`"completed`"]` and a successful response.
- [ ] **Curl test:** terminal showing HTTP response with completed, pending, total, and completion percentage.
- [ ] **Flask mocked test:** PyTest output showing the mocked `/stats` test passing.
- [ ] **CloudWatch Lambda logs:** `/aws/lambda/cloudtask-dev-stats` log stream showing structured `task_stats_calculated` JSON.
- [ ] **Lambda error alarm:** CloudWatch alarm page showing the Lambda Errors metric alarm.

## 7. IAM and account security

- [ ] **EC2 IAM role:** role name and attached policy showing S3 read and CloudWatch log write permissions.
- [ ] **EC2 instance profile:** profile attached to the CloudTask EC2 instance.
- [ ] **Lambda IAM role:** role showing Lambda basic execution/logging permissions only.
- [ ] **S3 public access block:** all four public access block settings enabled.
- [ ] **MFA enabled:** IAM user or identity center security page showing MFA enabled; redact recovery codes and sensitive identifiers.
- [ ] **No secrets in repository:** Jenkins Secrets check passed and no `.env` or private key appears in the GitHub repository.

## 8. Cost management

- [ ] **AWS Budget:** budget name, monthly limit, and email notification configuration.
- [ ] **Budget thresholds:** notifications visible at 50%, 80%, and 100%.
- [ ] **Cost Explorer overview:** monthly cost grouped by AWS service.
- [ ] **Cost Explorer region filter:** `ap-south-1` filter and relevant usage type visible.
- [ ] **Idle/oversized analysis:** EC2, EBS, S3, public IPv4, or data-transfer cost detail supporting an optimization decision.
- [ ] **Destroy command:** terminal showing `terraform destroy -var-file=terraform.tfvars` after the demo, without exposing credentials.

## Evidence quality checklist

- [ ] Every screenshot has a figure number and one-sentence caption.
- [ ] Dates, AWS region, Jenkins build number, and image tag are visible where relevant.
- [ ] Secrets, tokens, passwords, private keys, cookies, and unnecessary account IDs are redacted.
- [ ] Passing and deliberate-failure screenshots are clearly labeled.
- [ ] The final report connects each screenshot to a requirement, test, or operational decision.
