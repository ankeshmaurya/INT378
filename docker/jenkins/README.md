# Local Jenkins

Build and start Jenkins from the repository root:

```powershell
docker compose -f docker/jenkins/docker-compose.yml up --build -d
```

Open `http://localhost:8080`. Retrieve the first administrator password with:

```powershell
docker compose -f docker/jenkins/docker-compose.yml exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

The Jenkins container mounts `/var/run/docker.sock`, allowing pipeline Docker builds to use the host Docker engine. On Linux, ensure the Jenkins process can access the socket. On Docker Desktop, start the Linux engine before starting Jenkins.

Stop Jenkins without deleting its configuration:

```powershell
docker compose -f docker/jenkins/docker-compose.yml down
```
