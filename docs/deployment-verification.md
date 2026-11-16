# CloudTask deployment verification

## Preconditions

- Terraform has created the EC2 instance and security group.
- `terraform output ec2_public_ip` returns the instance address.
- `ssh_cidr` is your current public IP with `/32`.
- `monitoring_cidr` is limited to the administrator or monitoring network.
- The EC2 instance has the repository at `/opt/cloudtask` (or the Jenkins `EC2_APP_DIR` value).
- `/opt/cloudtask/.env` exists on EC2 with `SECRET_KEY`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `APP_PORT`.
- `APP_PORT` is `5000` or `8000` and matches the Terraform `app_port` variable. Port 80 always forwards to the container's port 5000.

## Push to live deployment

1. Make a small visible change, such as updating a page title.
2. Run the local checks:

   ```powershell
   python -m pytest
   ```

3. Commit and push to the branch connected to the Jenkins job:

   ```powershell
   git add .
   git commit -m "Deploy CloudTask change"
   git push origin main
   ```

4. In Jenkins, open the triggered build and watch these stages in order:
   `Checkout`, `Install dependencies`, `Secrets check`, `Run PyTest`, `Code Security Scan`, `Docker Build`, `Trivy Image Scan`, `Docker Hub Push`, and `Deploy to EC2`.
5. Confirm the build-number image and `latest` tag are pushed only after Bandit and Trivy pass.
6. Confirm the deployment stage reports a successful health check.
7. Verify the public endpoint using the Terraform output IP:

   ```powershell
   $ip = terraform -chdir=terraform output -raw ec2_public_ip
   curl.exe -i "http://$ip/health"
   ```

   Expect HTTP 200, `{"status":"ok"}`, and an `X-CloudTask-Version` header containing the Docker Hub repository and Jenkins build number, for example `mydockeruser/cloudtask:42`.
8. Verify the image build metadata and deployment gate:

   ```powershell
   curl.exe "http://$ip/version"
   ```

   Expect JSON containing `build_number`, `git_commit`, and `build_time`; `build_number` must equal the Jenkins build that deployed the image. The Jenkins deploy stage performs this check on the EC2 instance and rolls back on mismatch.
9. Confirm the service on EC2:

   ```bash
   cd /opt/cloudtask
   CLOUDTASK_IMAGE=mydockeruser/cloudtask:42 docker compose --env-file .env -f docker/docker-compose.yml ps
   CLOUDTASK_IMAGE=mydockeruser/cloudtask:42 docker compose --env-file .env -f docker/docker-compose.yml logs --tail=100 app
   ```

## Automatic rollback

The Jenkins deploy stage records the image currently running before pulling the new image. If Compose fails to start the new image or the local `http://127.0.0.1/health` check fails, Jenkins starts the previous image again and fails the build. The failed build must not be treated as a release.

## Manual rollback

1. Identify the last known-good Jenkins build number, for example `41`.
2. SSH to EC2:

   ```bash
   ssh ubuntu@EC2_PUBLIC_IP
   ```

3. Pull and restart the known-good image:

   ```bash
   cd /opt/cloudtask
   export CLOUDTASK_IMAGE=mydockeruser/cloudtask:41
   docker compose --env-file .env -f docker/docker-compose.yml pull app
   docker compose --env-file .env -f docker/docker-compose.yml up -d --no-build app db
   curl --fail http://127.0.0.1/health
   ```

4. Confirm the public endpoint's `X-CloudTask-Version` header reports the rollback tag.
5. Investigate the failed build before retrying deployment. Never overwrite the known-good image tag.

## Expected fail-fast behavior

- A `.env`, credential, `.pem`, or `.key` file stops the Secrets check.
- A high-severity Bandit finding stops before Docker Build.
- A HIGH or CRITICAL Trivy finding stops before Docker Hub Push.
- A failed EC2 startup or health check triggers rollback and prevents a successful build result.
