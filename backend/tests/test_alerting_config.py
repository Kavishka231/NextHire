from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_prometheus_loads_rules_alertmanager_and_host_metrics():
    config = read("observability/prometheus/prometheus.yml")
    assert "/etc/prometheus/alerts.yml" in config
    assert "alertmanager:9093" in config
    assert "node-exporter:9100" in config


def test_required_alert_thresholds_are_defined():
    rules = read("observability/prometheus/alerts.yml")
    for alert in (
        "NextHireApiHighErrorRate",
        "NextHireDatabaseUnavailable",
        "NextHireRedisUnavailable",
        "NextHireCeleryTaskFailures",
        "NextHireDiskSpaceLow",
    ):
        assert f"alert: {alert}" in rules
    assert "> 0.05" in rules
    assert "> 0.80" in rules
    assert "> 0.90" in rules


def test_percentage_alerts_have_minimum_traffic_guards():
    rules = read("observability/prometheus/alerts.yml")
    assert 'increase(nexthire_http_requests_total{route=~"/api/.*"}[5m])) >= 20' in rules
    assert 'increase(nexthire_http_requests_total{route=~"/api/.*"}[30m])) >= 100' in rules


def test_alertmanager_uses_secret_backed_webhook_and_resolutions():
    config = read("observability/alertmanager/alertmanager.yml")
    assert "url_file: /run/secrets/alert-webhook-url" in config
    assert "send_resolved: true" in config
    assert "url:" not in config
