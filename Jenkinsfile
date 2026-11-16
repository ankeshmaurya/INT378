pipeline {
  agent any

  options {
    skipDefaultCheckout(true)
    timestamps()
    disableConcurrentBuilds()
    skipStagesAfterUnstable()
    buildDiscarder(logRotator(numToKeepStr: '20'))
  }

  parameters {
    string(name: 'DOCKERHUB_REPOSITORY', defaultValue: '', description: 'Docker Hub repository, for example your-user/cloudtask')
    string(name: 'EC2_HOST', defaultValue: '', description: 'Public DNS name or IP address of the EC2 instance')
    string(name: 'EC2_USER', defaultValue: 'ubuntu', description: 'SSH user for the EC2 instance')
    string(name: 'EC2_APP_DIR', defaultValue: '/opt/cloudtask', description: 'Directory containing the CloudTask repository and .env on EC2')
  }

  triggers {
    githubPush()
  }

  environment {
    IMAGE_TAG = "${params.DOCKERHUB_REPOSITORY}:${env.BUILD_NUMBER}"
    IMAGE_LATEST = "${params.DOCKERHUB_REPOSITORY}:latest"
  }

  stages {
    stage('Checkout') {
      steps {
        checkout scm
        script {
          env.GIT_COMMIT = sh(script: 'git rev-parse HEAD', returnStdout: true).trim()
          if (!params.DOCKERHUB_REPOSITORY?.trim()) {
            error('DOCKERHUB_REPOSITORY must be configured before building.')
          }
          if (!params.EC2_HOST?.trim()) {
            error('EC2_HOST must be configured before deployment.')
          }
        }
      }
    }

    stage('Install dependencies') {
      steps {
        sh 'python3 -m venv .venv-ci && .venv-ci/bin/pip install --no-cache-dir -r requirements.txt'
      }
    }

    stage('Secrets check') {
      steps {
        sh '''
          set -eu
          : > secrets-report.txt
          find . -path './.git' -prune -o -type f \( \
            -name '.env' -o \
            -iname '*credentials*' -o \
            -iname '*.pem' -o \
            -iname '*.key' \
          \) -print > secrets-report.txt
          if [ -s secrets-report.txt ]; then
            echo 'Potential secret files found:'
            cat secrets-report.txt
            exit 1
          fi
          echo 'No .env, credential, PEM, or private key files found.'
        '''
      }
    }

    stage('Run PyTest') {
      steps {
        sh '.venv-ci/bin/pytest'
      }
      post {
        always {
          junit allowEmptyResults: false, testResults: 'test-results.xml'
          recordCoverage(tools: [[parser: 'COBERTURA', pattern: 'coverage.xml']])
        }
      }
    }

    stage('Code Security Scan') {
      steps {
        sh '.venv-ci/bin/bandit --recursive app --severity-level high --format json --output bandit-report.json'
      }
    }

    stage('Docker Build') {
      steps {
        sh '''
          set -eu
          BUILD_TIME="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
          docker build \
            --file docker/Dockerfile \
            --build-arg BUILD_NUMBER="$BUILD_NUMBER" \
            --build-arg GIT_COMMIT="$GIT_COMMIT" \
            --build-arg BUILD_TIME="$BUILD_TIME" \
            --tag "$IMAGE_TAG" \
            --tag "$IMAGE_LATEST" .
        '''
      }
    }

    stage('Trivy Image Scan') {
      steps {
        sh '''
          docker run --rm \
            --volume /var/run/docker.sock:/var/run/docker.sock \
            --volume "$WORKSPACE:/src" \
            aquasec/trivy:0.57.1 image \
            --scanners vuln \
            --severity HIGH,CRITICAL \
            --exit-code 1 \
            --format json \
            --output /src/trivy-report.json \
            "$IMAGE_TAG"
        '''
      }
    }

    stage('Docker Hub Push') {
      steps {
        withCredentials([usernamePassword(credentialsId: 'dockerhub-creds', usernameVariable: 'DOCKERHUB_USERNAME', passwordVariable: 'DOCKERHUB_PASSWORD')]) {
          sh '''
            set -eu
            printf '%s' "$DOCKERHUB_PASSWORD" | docker login --username "$DOCKERHUB_USERNAME" --password-stdin
            docker push "$IMAGE_TAG"
            docker push "$IMAGE_LATEST"
            docker logout
          '''
        }
      }
    }

    stage('Deploy to EC2') {
      steps {
        withCredentials([usernamePassword(credentialsId: 'dockerhub-creds', usernameVariable: 'DOCKERHUB_USERNAME', passwordVariable: 'DOCKERHUB_PASSWORD')]) {
          sshagent(credentials: ['ec2-ssh-key']) {
            sh '''
set -eu
ssh -o StrictHostKeyChecking=accept-new "$EC2_USER@$EC2_HOST" \
  "mkdir -p '$EC2_APP_DIR/docker'"
scp -o StrictHostKeyChecking=accept-new docker/docker-compose.yml \
  "$EC2_USER@$EC2_HOST:$EC2_APP_DIR/docker/docker-compose.yml"
scp -o StrictHostKeyChecking=accept-new docker/prometheus.yml docker/alert_rules.yml \
  "$EC2_USER@$EC2_HOST:$EC2_APP_DIR/docker/"
scp -r -o StrictHostKeyChecking=accept-new docker/grafana \
  "$EC2_USER@$EC2_HOST:$EC2_APP_DIR/docker/"
printf '%s' "$DOCKERHUB_PASSWORD" | ssh -o StrictHostKeyChecking=accept-new "$EC2_USER@$EC2_HOST" \
  "docker login --username '$DOCKERHUB_USERNAME' --password-stdin"
ssh -o StrictHostKeyChecking=accept-new "$EC2_USER@$EC2_HOST" \
  "CLOUDTASK_IMAGE='$IMAGE_TAG' EXPECTED_BUILD_NUMBER='$BUILD_NUMBER' EC2_APP_DIR='$EC2_APP_DIR' bash -s" <<'REMOTE_SCRIPT'
set -eu
cd "$EC2_APP_DIR"
previous_image=$(docker compose --env-file .env -f docker/docker-compose.yml ps -q app | xargs -r docker inspect --format '{{.Config.Image}}' 2>/dev/null || true)
CLOUDTASK_IMAGE="$CLOUDTASK_IMAGE" docker compose --env-file .env -f docker/docker-compose.yml pull app
rollback() {
  if [ -n "$previous_image" ]; then
    echo "Deployment failed; restoring $previous_image"
    CLOUDTASK_IMAGE="$previous_image" docker compose --env-file .env -f docker/docker-compose.yml up -d --no-build app db || true
  fi
}
if ! CLOUDTASK_IMAGE="$CLOUDTASK_IMAGE" docker compose --env-file .env -f docker/docker-compose.yml up -d --no-build app db; then
  rollback
  exit 1
fi
if ! curl --fail --silent --show-error --retry 10 --retry-delay 3 http://127.0.0.1/health; then
  rollback
  exit 1
fi
version_response=$(curl --fail --silent --show-error --retry 10 --retry-delay 3 http://127.0.0.1/version)
version_build=$(printf '%s' "$version_response" | sed -n 's/.*"build_number"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
if [ "$version_build" != "$EXPECTED_BUILD_NUMBER" ]; then
  echo "Version check failed: expected build $EXPECTED_BUILD_NUMBER, got $version_build"
  rollback
  exit 1
fi
docker image prune --force
docker logout
REMOTE_SCRIPT
            '''
          }
        }
      }
    }
  }

  post {
    success {
      echo "CloudTask build ${env.BUILD_NUMBER} passed tests, was pushed, and deployment completed."
    }
    failure {
      echo "CloudTask build ${env.BUILD_NUMBER} failed. Later stages were skipped; inspect the failed stage and test reports."
    }
    always {
      archiveArtifacts artifacts: 'coverage.xml,test-results.xml,bandit-report.json,trivy-report.json,secrets-report.txt', allowEmptyArchive: true
    }
  }
}
