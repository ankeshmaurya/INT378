# Serverless task statistics

Terraform creates a Python 3.11 Lambda, an API Gateway HTTP API, and the endpoint:

```text
POST https://<api-id>.execute-api.ap-south-1.amazonaws.com/stats
```

## Deploy

From the repository root:

```powershell
cd terraform
terraform init
terraform plan -var-file=terraform.tfvars
terraform apply -var-file=terraform.tfvars
terraform output -raw stats_api_url
```

Set the output URL in the Flask environment file:

```text
STATS_API_URL=https://<api-id>.execute-api.ap-south-1.amazonaws.com/stats
```

Restart the Flask or Docker Compose app after changing `.env`.

## Test with curl

```powershell
$statsUrl = terraform -chdir=terraform output -raw stats_api_url
curl.exe -X POST $statsUrl -H "Content-Type: application/json" -d '["completed","pending","completed"]'
```

Expected response:

```json
{"completed":2,"pending":1,"total":3,"completion_percentage":66.67}
```

The authenticated Flask dashboard sends the current user's statuses to the same URL when **View statistics** is selected. The Flask route does not expose another user's tasks.

## CloudWatch logs and alarm

Open AWS Console in `ap-south-1`, then go to **CloudWatch > Logs > Log groups** and open:

```text
/aws/lambda/cloudtask-dev-stats
```

Each invocation writes structured JSON events such as `task_stats_calculated` or `invalid_request`. The Terraform alarm is named `cloudtask-dev-stats-lambda-errors` and monitors the Lambda `Errors` metric over a five-minute period. Configure an SNS action separately if email or paging notifications are required.
