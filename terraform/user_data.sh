#!/bin/bash
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y ca-certificates curl docker.io docker-compose-v2
systemctl enable --now docker
usermod -aG docker ubuntu

mkdir -p /opt/cloudtask
mkdir -p /opt/cloudtask/docker
chown ubuntu:ubuntu /opt/cloudtask
chown ubuntu:ubuntu /opt/cloudtask/docker
