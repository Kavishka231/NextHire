# Alerting secrets

Create `alert-webhook-url` in this directory on the deployment host. The file
must contain one HTTPS endpoint that accepts Alertmanager's generic webhook
payload. Set mode `600`; the file is ignored by Git.

Alternatively set `ALERT_WEBHOOK_URL_FILE` to an absolute host path before
starting the observability Compose profile. Never commit notification tokens or
webhook URLs.
