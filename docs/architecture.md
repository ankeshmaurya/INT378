# CloudTask architecture

CloudTask is a small Flask application with a deliberately visible DevSecOps path.

- **App:** Flask factory, Flask-Login, SQLAlchemy, SQLite for local work and PostgreSQL in Compose.
- **Delivery:** Jenkins runs tests, Bandit, Docker build, Trivy, then push/deploy only on `main`. Every stage is fail-fast.
- **Infrastructure:** Terraform is primary and provisions a VPC, public app subnet, restricted security group, EC2 instance, encrypted private S3 artifact bucket, least-privilege EC2 metrics policy, logs, and a monthly budget alert.
- **Comparison:** `cloudformation/cloudtask.yml` demonstrates the equivalent foundational AWS resources without becoming the primary path.
- **Observability:** `/health` and `/metrics`, Prometheus scraping, Node Exporter host metrics, Grafana datasource support.
- **Serverless comparison:** `lambda/health_handler.py` is a minimal API Gateway-compatible health handler. Lambda/API Gateway/CloudWatch wiring can be added as a separate serverless deployment boundary.

AWS Cost Explorer is an account-level reporting service rather than a resource Terraform creates. Use it with the budget and CloudWatch resources to review spend.
