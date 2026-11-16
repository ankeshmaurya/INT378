# EC2 monitoring

The EC2 Compose stack runs Node Exporter, Prometheus, and Grafana alongside CloudTask.

- Node Exporter reads host CPU, memory, disk, and network metrics.
- Prometheus scrapes `node-exporter:9100` and `app:5000/metrics` every 15 seconds.
- CloudTask exposes request totals by method, route template, and status; request duration histograms; task event counters; and the current open-task gauge.
- Alert rules fire after 5 minutes above 80% CPU, 85% memory, 85% root disk usage, or 5% HTTP 5xx error rate.
- Grafana provisions the Prometheus datasource and the `CloudTask EC2 Overview` dashboard automatically.

## Gunicorn metrics

The production image runs two Gunicorn workers and sets `PROMETHEUS_MULTIPROC_DIR` to a
container-local temporary directory. The entrypoint clears stale metric files before
starting Gunicorn, and `/metrics` uses Prometheus's `MultiProcessCollector` to aggregate
counters and histograms from all workers. The open-task gauge is queried directly from
the database during each scrape, so it is not duplicated or made stale by worker-local
gauge files. No user identifiers are used as metric labels.

## Open Grafana

1. Confirm Terraform allowed TCP 3000 from your `monitoring_cidr`.
2. Find the instance address:

   ```powershell
   terraform -chdir=terraform output -raw ec2_public_ip
   ```

3. Open `http://EC2_PUBLIC_IP:3000` from a host inside the allowed monitoring CIDR.
4. Log in with username `admin` and the `GRAFANA_ADMIN_PASSWORD` value from the EC2 `.env` file.
5. Open **Dashboards > CloudTask > CloudTask EC2 Overview**.

The dashboard shows CPU, memory, root disk, network receive/transmit, request rate,
5xx error rate, p95 request latency, and task creation/completion rates. The Prometheus
datasource is automatically selected; no manual datasource setup is needed.

If Grafana does not load, check the EC2 security group, then run:

```bash
cd /opt/cloudtask
docker compose --env-file .env -f docker/docker-compose.yml ps
docker compose --env-file .env -f docker/docker-compose.yml logs --tail=100 prometheus grafana node-exporter
```
