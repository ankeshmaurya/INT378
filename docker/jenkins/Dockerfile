FROM jenkins/jenkins:lts-jdk17

USER root

RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
        docker.io \
        git \
        openssh-client \
        python3 \
        python3-pip \
        python3-venv \
    && rm -rf /var/lib/apt/lists/*

COPY docker/jenkins/plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli --plugin-file /usr/share/jenkins/ref/plugins.txt

RUN groupadd --system docker-host || true \
    && usermod --append --groups docker-host jenkins

USER jenkins
