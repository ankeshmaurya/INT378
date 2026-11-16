# CloudTask

CloudTask is a cloud-native student task management system for the LPU INT378 DevSecOps project. The application deliberately stays small: users register and log in, then add, view, edit, complete, delete, and analyze their own tasks. The engineering focus is the delivery system around it: testing, security scanning, containers, infrastructure as code, monitoring, serverless statistics, cost controls, and deployment rollback.

## What is included

- Flask application with Flask-Login and SQLAlchemy
- SQLite for local development and PostgreSQL in Docker/EC2 Compose
- Production multi-stage Docker image served by Gunicorn as a non-root user
- PyTest tests with in-memory SQLite, coverage XML, and JUnit XML
- Jenkins declarative pipeline with secrets check, Bandit, Trivy, Docker Hub push, and EC2 deployment
- Terraform as the primary AWS infrastructure path in `ap-south-1`
- CloudFormation comparison template
- EC2 monitoring with Node Exporter, Prometheus, Grafana, alerts, and provisioning
- Lambda/API Gateway task statistics endpoint
- AWS Budget, S3 versioning, backup lifecycle, CloudWatch logs, and cost guidance

## Architecture

```text
                              +------------------+
                              |      GitHub      |
                              | source + webhook |
                              +--------+---------+
                                       |
                                       v
+-------------+       +---------------+----------------+
| Developer   | push  | Jenkins container              |
| workstation +------>| tests -> Bandit -> Docker      |
+-------------+       | build -> Trivy -> push -> SSH  |
                      +---------------+----------------+
                                      |
                                      | Docker Hub image tag
                                      v
                    +----------------+----------------+
                    | AWS EC2 public instance         |
                    | Docker Compose                  |
                    |                                  |
                    | CloudTask -> PostgreSQL         |
                    | Prometheus -> Grafana            |
                    | Node Exporter (host metrics)    |
                    +----------------+----------------+
                                      |
                                      v
                              +-------+-------+
                              | S3 backups    |
                              | + static data |
                              +---------------+
```

The serverless statistics path is separate from the main CRUD request path:

```text
Logged-in Flask user
        |
        | POST task statuses
        v
API Gateway HTTP API /stats
        |
        v
Lambda stats_handler.py -----> CloudWatch Logs + error alarm
        |
        v
completed / pending / percentage
```

## Repository map

```text
app/                         Flask application, templates, CSS, metrics
  auth.py                    registration, login, logout
  tasks.py                   task CRUD and /stats client
  monitoring.py              /health and /metrics
  version.py                 build metadata exposed by /version
lambda/                      Lambda handlers and unit tests
terraform/                   primary AWS infrastructure
cloudformation/              AWS-native comparison template
docker/                      production image, Compose, monitoring, Jenkins
tests/                       Flask tests and fixtures
jenkins/                     Jenkins-related repository space
Jenkinsfile                 root declarative pipeline
docs/                        runbooks, comparisons, monitoring, cost, demo evidence
```

## Prerequisites

Install or configure:

- Python 3.11 or newer
- Docker Desktop with the Linux engine enabled
- Terraform 1.6 or newer
- AWS CLI configured with a non-root deployment identity
- An AWS key pair and public key for EC2
- Jenkins access credentials for Docker Hub and EC2 SSH
- Optional: `cfn-lint` for the CloudFormation comparison

Never commit `.env`, private keys, AWS access keys, Terraform state, or database files.

## Phase 1: Run locally with SQLite

Copy the example environment file and set a long random secret:

```powershell
Copy-Item .env.example .env
```

Install dependencies and start Flask:

```powershell
python -m pip install -r requirements.txt
flask --app run:app db upgrade
python run.py
```

Open `http://localhost:5000`, register an account, and exercise task CRUD. The local SQLite database is created automatically. Verify the health and metrics endpoints:

```powershell
curl.exe http://localhost:5000/health
curl.exe http://localhost:5000/metrics
```

The `/stats` dashboard action requires `STATS_API_URL`; configure it after deploying the Lambda API in Phase 6.

## Phase 2: Run the application with Docker and PostgreSQL

Set these values in `.env`:

```text
SECRET_KEY=use-a-long-random-value
POSTGRES_DB=cloudtask
POSTGRES_USER=cloudtask
POSTGRES_PASSWORD=use-a-strong-password
GRAFANA_ADMIN_PASSWORD=use-a-strong-password
APP_PORT=5000
```

Start the local stack:

```powershell
docker compose --env-file .env -f docker/docker-compose.yml up --build
```

Services:

- CloudTask: `http://localhost:5000`
- Health: `http://localhost:5000/health`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000`
- Node Exporter: `http://localhost:9100`
- PostgreSQL: internal Compose service `db`

Stop the stack without deleting named volumes:

```powershell
docker compose --env-file .env -f docker/docker-compose.yml down
```

## Phase 3: Provision AWS with Terraform

Terraform is the primary infrastructure path. It creates the VPC, public subnet, route table, internet gateway, security group, EC2 instance, key pair, encrypted/versioned S3 bucket, IAM roles, Lambda/API Gateway resources, CloudWatch logs, budget, and lifecycle rules.

Create variables from the example:

```powershell
Copy-Item terraform/terraform.tfvars.example terraform/terraform.tfvars
```

Set at least:

```hcl
aws_region            = "ap-south-1"
ssh_cidr              = "YOUR_PUBLIC_IP/32"
monitoring_cidr       = "YOUR_MONITORING_IP/32"
public_key            = "YOUR_OPENSSH_PUBLIC_KEY"
monthly_budget_limit  = 25
budget_email          = "your-email@example.com"
```

Initialize and validate:

```powershell
terraform -chdir=terraform init
terraform -chdir=terraform fmt -check
terraform -chdir=terraform validate
```

Review and apply:

```powershell
terraform -chdir=terraform plan -var-file=terraform.tfvars
terraform -chdir=terraform apply -var-file=terraform.tfvars
```

Save the important outputs:

```powershell
terraform -chdir=terraform output ec2_public_ip
terraform -chdir=terraform output bucket_name
terraform -chdir=terraform output stats_api_url
```

The EC2 user-data script installs Docker and Docker Compose and prepares `/opt/cloudtask`. It does not copy secrets. The EC2 `.env` must be created securely on the instance before starting the stack.
The production Docker entrypoint runs `flask db upgrade` before Gunicorn, so schema migrations are applied automatically on container startup.

## Phase 4: Configure local Jenkins

Jenkins can run in a container with access to the host Docker engine:

```powershell
docker compose -f docker/jenkins/docker-compose.yml up --build -d
```

Open `http://localhost:8080`. Retrieve the initial password:

```powershell
docker compose -f docker/jenkins/docker-compose.yml exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

Follow [docker/jenkins/SETUP.md](docker/jenkins/SETUP.md) to create:

- `dockerhub-creds`: Docker Hub username and access token
- `ec2-ssh-key`: EC2 SSH username and private key

The Jenkins job must use **Pipeline script from SCM** and the root `Jenkinsfile`.

## Phase 5: Trigger and understand the pipeline

Configure the GitHub webhook for:

```text
http://YOUR_JENKINS_HOST/github-webhook/
```

Use `application/json` and select the push event. Configure the Jenkins parameters:

- `DOCKERHUB_REPOSITORY`, for example `mydockeruser/cloudtask`
- `EC2_HOST`, the EC2 public IP or DNS name
- `EC2_USER`, normally `ubuntu`
- `EC2_APP_DIR`, normally `/opt/cloudtask`

Push a commit:

```powershell
git add .
git commit -m "Deploy CloudTask change"
git push origin main
```

Pipeline flow:

```text
Checkout
   -> Install dependencies
   -> Secrets check
   -> Run PyTest + JUnit + coverage
   -> Code Security Scan (Bandit)
   -> Docker Build
   -> Trivy Image Scan
   -> Docker Hub Push (build number + latest)
   -> Deploy to EC2 -> /health + /version verification + health check
```

The Docker image embeds the Jenkins build number, checked-out Git commit, and UTC
build time. They are available at `/version`, and the web footer shows the build
number. The deploy stage fails and rolls back if `/version` does not report the
current Jenkins build number.

The pipeline fails fast. Secrets, high-severity Bandit findings, HIGH/CRITICAL Trivy findings, failed tests, failed image startup, or failed health checks prevent a successful release. Deployment automatically restores the previously running image when startup or health verification fails.

## Phase 6: Configure and test Lambda statistics

After Terraform applies the serverless resources, set the output URL in the local or EC2 `.env`:

```text
STATS_API_URL=https://API_ID.execute-api.ap-south-1.amazonaws.com/stats
```

Test directly:

```powershell
$statsUrl = terraform -chdir=terraform output -raw stats_api_url
curl.exe -X POST $statsUrl -H "Content-Type: application/json" -d "[`"completed`",`"pending`",`"completed`"]"
```

Expected response:

```json
{"completed":2,"pending":1,"total":3,"completion_percentage":66.67}
```

The logged-in Flask dashboard sends the current user's task statuses when **View statistics** is selected.

## Phase 7: Access monitoring

Find the EC2 address:

```powershell
terraform -chdir=terraform output -raw ec2_public_ip
```

From a host allowed by `monitoring_cidr`, open:

```text
http://EC2_PUBLIC_IP:3000
```

Log in as `admin` using `GRAFANA_ADMIN_PASSWORD` from the EC2 `.env`. Open **Dashboards > CloudTask > CloudTask EC2 Overview**. The provisioned dashboard shows CPU, memory, root disk, network traffic, and Flask request rate.

Prometheus scrapes Node Exporter and the Flask `/metrics` endpoint. Alert rules fire after five minutes above 80% CPU, 85% memory, or 85% root disk usage. Details are in [docs/monitoring.md](docs/monitoring.md).

## Tests and reports

Run the Flask and Lambda tests:

```powershell
python -m pytest tests lambda/test_stats_handler.py
```

The test configuration produces:

- `coverage.xml`
- `test-results.xml`
- terminal coverage output

Security checks used by Jenkins:

```powershell
bandit --recursive app --severity-level high
trivy image --severity HIGH,CRITICAL your-user/cloudtask:TAG
```

## CloudFormation comparison

Validate and deploy the AWS-native comparison template:

```powershell
cfn-lint cloudformation/cloudtask.yml
aws cloudformation deploy `
  --template-file cloudformation/cloudtask.yml `
  --stack-name cloudtask-comparison `
  --region ap-south-1 `
  --parameter-overrides ProjectName=cloudtask AmiId=AMI_ID KeyName=KEY_NAME SshCidr=YOUR_IP/32 MonitoringCidr=YOUR_MONITORING_CIDR/32 AppPort=5000
```

See [docs/terraform-vs-cloudformation.md](docs/terraform-vs-cloudformation.md) for the comparison.

## Cost controls and teardown

Terraform creates an AWS Budget with notifications at 50%, 80%, and 100% of `monthly_budget_limit`. Cost Explorer guidance and the S3 backup lifecycle are documented in [docs/cost-optimization.md](docs/cost-optimization.md).

Destroy demo infrastructure when finished:

```powershell
terraform -chdir=terraform destroy -var-file=terraform.tfvars
```

The S3 bucket is protected from force deletion. Confirm backups and static assets are no longer needed, empty the bucket and old versions, then remove it deliberately. Stop EC2 for a short pause, or destroy the full Terraform environment for longer gaps.

## Supporting documentation

- [docs/architecture.md](docs/architecture.md)
- [docs/deployment-verification.md](docs/deployment-verification.md)
- [docs/monitoring.md](docs/monitoring.md)
- [docs/serverless-stats.md](docs/serverless-stats.md)
- [docs/cost-optimization.md](docs/cost-optimization.md)
- [docker/jenkins/SETUP.md](docker/jenkins/SETUP.md)
- [docs/demo-checklist.md](docs/demo-checklist.md)
