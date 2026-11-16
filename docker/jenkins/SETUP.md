# Jenkins setup

## 1. Start Jenkins

From the repository root, start Docker Desktop's Linux engine and run:

```powershell
docker compose -f docker/jenkins/docker-compose.yml up --build -d
```

Open `http://localhost:8080`. Get the initial password with:

```powershell
docker compose -f docker/jenkins/docker-compose.yml exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

The image installs the plugins listed in `plugins.txt`. The Docker socket mount lets the pipeline build and push images through the host Docker engine.

## 2. Add credentials

In **Manage Jenkins > Credentials > System > Global credentials**, create:

1. `dockerhub-creds`: **Username with password**, using the Docker Hub username and an access token as the password.
2. `ec2-ssh-key`: **SSH Username with private key**, using `ubuntu` (or the EC2 login user) and the private key matching the public key installed on the instance.

Never commit either credential or a private key to the repository.

## 3. Create the pipeline job

1. Select **New Item**, choose **Pipeline**, and name it `CloudTask`.
2. In **Pipeline**, select **Pipeline script from SCM**.
3. Select **Git**, enter the repository URL and branch, and set the script path to `Jenkinsfile`.
4. Save, then configure these pipeline parameters when prompted: `DOCKERHUB_REPOSITORY`, `EC2_HOST`, `EC2_USER`, and `EC2_APP_DIR`.
5. Set `DOCKERHUB_REPOSITORY` to the full repository, such as `mydockeruser/cloudtask`.

The EC2 host must already contain the checked-out project at `EC2_APP_DIR`, a production `.env`, Docker, and Docker Compose. The deploy stage pulls the build-number image and restarts only the app and database services.

## 4. Configure the GitHub webhook

1. In GitHub, open **Settings > Webhooks > Add webhook**.
2. Set the payload URL to `http://YOUR_JENKINS_HOST/github-webhook/`.
3. Set content type to `application/json`.
4. Choose **Just the push event** and save.
5. Ensure Jenkins is reachable from GitHub, or expose it through a secure tunnel/reverse proxy.

The root `Jenkinsfile` uses `githubPush()` so a push triggers the pipeline. Tests, the secrets check, and Bandit happen before the Docker build. Trivy runs after the build but before Docker Hub push and EC2 deployment; a failed stage prevents all later stages.

## 5. Security reports and deliberate failures

The pipeline archives `bandit-report.json`, `trivy-report.json`, `secrets-report.txt`, `coverage.xml`, and `test-results.xml` from every build when they exist. Review them from the Jenkins build page under **Build Artifacts**.

To demonstrate the secrets gate, create a temporary untracked file named `.env` in the repository and push it to a presentation branch. The **Secrets check** stage fails before tests or Docker build. Remove the file after the demonstration and rotate any exposed values.

To demonstrate the Bandit gate, add a temporary high-severity test finding such as an unsafe `subprocess` call with `shell=True` under `app/`. The **Code Security Scan** stage fails and archives `bandit-report.json`.

To demonstrate the Trivy gate, temporarily change the first line of `docker/Dockerfile` to an obsolete base such as `python:3.9-slim-buster`, commit it on a demonstration branch, and run the pipeline. Trivy should report HIGH or CRITICAL operating-system vulnerabilities and stop before **Docker Hub Push**. Restore `python:3.11-slim` afterward and rebuild the Jenkins image if needed.
