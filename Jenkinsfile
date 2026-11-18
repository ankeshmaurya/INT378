
pipeline {
  agent {
    label 'windows-docker'
  }

  options {
    skipDefaultCheckout(true)
    timestamps()
    disableConcurrentBuilds()
    skipStagesAfterUnstable()
    buildDiscarder(logRotator(numToKeepStr: '20'))
  }

  parameters {
    string(
      name: 'DOCKERHUB_REPOSITORY',
      defaultValue: '',
      description: 'Docker Hub repository, for example ankeshmaurya/cloudtask'
    )
    string(
      name: 'EC2_HOST',
      defaultValue: '',
      description: 'Public DNS name or IP address of EC2'
    )
    string(
      name: 'EC2_USER',
      defaultValue: 'ubuntu',
      description: 'SSH user for EC2'
    )
    string(
      name: 'EC2_APP_DIR',
      defaultValue: '/opt/cloudtask',
      description: 'CloudTask application directory on EC2'
    )
  }

  triggers {
    githubPush()
  }

  environment {
    DOCKERHUB_REPOSITORY = 'ankeshmaurya/cloudtask'
    IMAGE_TAG = "${params.DOCKERHUB_REPOSITORY}:${env.BUILD_NUMBER}"
    IMAGE_LATEST = "${params.DOCKERHUB_REPOSITORY}:latest"
  }

  stages {

    stage('Checkout') {
      steps {
        checkout scm

        script {
          env.GIT_COMMIT = bat(
            script: '@echo off\r\ngit rev-parse HEAD',
            returnStdout: true
          ).trim()

          
          if (!params.DOCKERHUB_REPOSITORY?.trim()) {
              error('DOCKERHUB_REPOSITORY is required.')
          }
          
          if (!params.DOCKERHUB_REPOSITORY.matches('[a-z0-9][a-z0-9._-]*/[a-z0-9][a-z0-9._-]*')) {
              error('Invalid Docker Hub repository format.')
          }
          
          if (!params.EC2_HOST?.trim()) {
              error('EC2_HOST is required.')
          }
          
          if (!params.EC2_HOST.matches('[A-Za-z0-9.-]+')) {
              error('Invalid EC2 host format.')
          }
          
          if (!params.EC2_USER.matches('[A-Za-z_][A-Za-z0-9_-]*')) {
              error('Invalid EC2 username.')
          }
          
          if (!params.EC2_APP_DIR.matches('/[A-Za-z0-9._/-]+')) {
              error('Invalid EC2 application directory.')
          }

        }
      }
    }

    stage('Install dependencies') {
      steps {
        powershell '''
          $ErrorActionPreference = 'Stop'

          python --version

          python -m venv .venv-ci

          & .\\.venv-ci\\Scripts\\python.exe -m pip install --no-cache-dir -r requirements.txt

          if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
          }
        '''
      }
    }

    stage('Secrets check') {
      steps {
        powershell '''
          $ErrorActionPreference = 'Stop'

          $root = (Get-Location).Path
          $report = Join-Path $root 'secrets-report.txt'

          $excluded = '\\\\(\\.git|venv|\\.venv|\\.venv-ci|node_modules)(\\\\|$)'

          $files = Get-ChildItem -Path $root -Recurse -File -Force |
            Where-Object {
              $_.FullName -notmatch $excluded -and
              (
                $_.Name -eq '.env' -or
                $_.Name -match 'credentials' -or
                $_.Extension -in @('.pem', '.key')
              )
            }

          if ($files) {
            $files.FullName | Set-Content -Path $report
            Write-Host 'Potential secret files found.'
            Get-Content $report
            exit 1
          }

          'No potential secret files found.' | Set-Content $report
          Write-Host 'Secrets check passed.'
        '''
      }
    }

    stage('Run PyTest') {
      steps {
        powershell '''
          $ErrorActionPreference = 'Stop'

          & .\\.venv-ci\\Scripts\\python.exe -m pytest

          if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
          }
        '''
      }

      post {
        always {
          junit(
            allowEmptyResults: false,
            testResults: 'test-results.xml'
          )

          recordCoverage(
            tools: [[
              parser: 'COBERTURA',
              pattern: 'coverage.xml'
            ]]
          )
        }
      }
    }

    stage('Code Security Scan') {
      steps {
        powershell '''
          $ErrorActionPreference = 'Stop'

          & .\\.venv-ci\\Scripts\\python.exe -m bandit `
            --recursive app `
            --severity-level high `
            --format json `
            --output bandit-report.json

          if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
          }
        '''
      }
    }

    stage('Docker Build') {
      steps {
        powershell '''
          $ErrorActionPreference = 'Stop'

          $buildTime = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")

          docker build `
            --file docker/Dockerfile `
            --build-arg "BUILD_NUMBER=$env:BUILD_NUMBER" `
            --build-arg "GIT_COMMIT=$env:GIT_COMMIT" `
            --build-arg "BUILD_TIME=$buildTime" `
            --tag "$env:IMAGE_TAG" `
            --tag "$env:IMAGE_LATEST" .

          if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
          }
        '''
      }
    }

    stage('Trivy Image Scan') {
      steps {
        powershell '''
          $ErrorActionPreference = 'Stop'

          & "C:\\Tools\\Trivy\\trivy.exe" image `
            --scanners vuln `
            --severity HIGH,CRITICAL `
            --exit-code 0 `
            --format json `
            --output trivy-report.json `
            "$env:IMAGE_TAG"

          if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
          }

          Write-Host 'Trivy scan completed. Vulnerability report generated.'
        '''
      }
    }

    stage('Docker Hub Push') {
      steps {
        withCredentials([
          usernamePassword(
            credentialsId: 'dockerhub-creds',
            usernameVariable: 'DOCKERHUB_USERNAME',
            passwordVariable: 'DOCKERHUB_PASSWORD'
          )
        ]) {
          powershell '''
            $ErrorActionPreference = 'Stop'

            try {
              $env:DOCKERHUB_PASSWORD |
                docker login --username $env:DOCKERHUB_USERNAME --password-stdin

              if ($LASTEXITCODE -ne 0) {
                exit $LASTEXITCODE
              }

              docker push "$env:IMAGE_TAG"

              if ($LASTEXITCODE -ne 0) {
                exit $LASTEXITCODE
              }

              docker push "$env:IMAGE_LATEST"

              if ($LASTEXITCODE -ne 0) {
                exit $LASTEXITCODE
              }
            }
            finally {
              docker logout
            }
          '''
        }
      }
    }

    stage('Deploy to EC2') {
      steps {
        withCredentials([
          usernamePassword(
            credentialsId: 'dockerhub-creds',
            usernameVariable: 'DOCKERHUB_USERNAME',
            passwordVariable: 'DOCKERHUB_PASSWORD'
          ),
          sshUserPrivateKey(
            credentialsId: 'ec2-ssh-key',
            keyFileVariable: 'SSH_KEY'
          )
        ]) {

          writeFile(
            file: 'remote-deploy.sh',
            text: '''#!/bin/bash
set -eu

cd "$EC2_APP_DIR"

previous_image=$(docker compose --env-file .env -f docker/docker-compose.yml ps -q app | xargs -r docker inspect --format '{{.Config.Image}}' 2>/dev/null || true)

CLOUDTASK_IMAGE="$CLOUDTASK_IMAGE" docker compose --env-file .env -f docker/docker-compose.yml pull app

rollback() {
  if [ -n "$previous_image" ]; then
    echo "Deployment failed. Restoring previous image: $previous_image"
    CLOUDTASK_IMAGE="$previous_image" docker compose --env-file .env -f docker/docker-compose.yml up -d --no-build app db || true
  fi
}

if ! CLOUDTASK_IMAGE="$CLOUDTASK_IMAGE" docker compose --env-file .env -f docker/docker-compose.yml up -d --no-build app db; then
  rollback
  exit 1
fi

if ! curl --fail --silent --show-error --retry 10 --retry-delay 3 http://127.0.0.1:5000/health; then
  rollback
  exit 1
fi

version_response=$(curl --fail --silent --show-error --retry 10 --retry-delay 3 http://127.0.0.1:5000/version)

version_build=$(printf '%s' "$version_response" | sed -n 's/.*"build_number"[[:space:]]*:[[:space:]]*"\\([^"]*\\)".*/\\1/p')

if [ "$version_build" != "$EXPECTED_BUILD_NUMBER" ]; then
  echo "Version check failed."
  echo "Expected: $EXPECTED_BUILD_NUMBER"
  echo "Received: $version_build"
  rollback
  exit 1
fi

echo "CloudTask deployment completed successfully."
docker logout || true
'''
          )

          powershell '''
            $ErrorActionPreference = 'Stop'

            $remote = "$env:EC2_USER@$env:EC2_HOST"
            $key = $env:SSH_KEY
            $dir = $env:EC2_APP_DIR

            function Check-ExitCode {
              if ($LASTEXITCODE -ne 0) {
                throw "SSH/SCP operation failed with exit code $LASTEXITCODE"
              }
            }

            # Prepare remote directory
            & ssh -i $key -o StrictHostKeyChecking=accept-new $remote "mkdir -p '$dir/docker'"
            Check-ExitCode

            # Transfer Docker Compose configuration
            & scp -i $key -o StrictHostKeyChecking=accept-new `
              docker/docker-compose.yml "${remote}:$dir/docker/docker-compose.yml"
            Check-ExitCode

            & scp -i $key -o StrictHostKeyChecking=accept-new `
              docker/prometheus.yml docker/alert_rules.yml "${remote}:$dir/docker/"
            Check-ExitCode

            & scp -r -i $key -o StrictHostKeyChecking=accept-new `
              docker/grafana "${remote}:$dir/docker/"
            Check-ExitCode

            # Authenticate Docker Hub on EC2
            $env:DOCKERHUB_PASSWORD |
              & ssh -i $key -o StrictHostKeyChecking=accept-new $remote `
              "docker login --username '$env:DOCKERHUB_USERNAME' --password-stdin"

            Check-ExitCode

            # Transfer deployment script
            $remoteScript = "/tmp/cloudtask-deploy-$env:BUILD_NUMBER.sh"

            & scp -i $key -o StrictHostKeyChecking=accept-new `
              remote-deploy.sh "${remote}:$remoteScript"
            Check-ExitCode

            # Execute deployment
            & ssh -i $key -o StrictHostKeyChecking=accept-new $remote `
              "chmod 700 '$remoteScript' && CLOUDTASK_IMAGE='$env:IMAGE_TAG' EXPECTED_BUILD_NUMBER='$env:BUILD_NUMBER' EC2_APP_DIR='$dir' bash '$remoteScript'; result=`$?; rm -f '$remoteScript'; exit `$result"

            Check-ExitCode
          '''
        }
      }
    }
  }

  post {
    success {
      echo "CloudTask build ${env.BUILD_NUMBER} completed successfully."
    }

    failure {
      echo "CloudTask build ${env.BUILD_NUMBER} failed. Inspect the failed stage and reports."
    }

    always {
      archiveArtifacts(
        artifacts: 'coverage.xml,test-results.xml,bandit-report.json,trivy-report.json,secrets-report.txt',
        allowEmptyArchive: true
      )
    }
  }
}
