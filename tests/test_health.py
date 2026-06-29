from http import HTTPStatus

from conftest import load_module

health = load_module("health_module", "bot/health.py")
HealthSnapshot = health.HealthSnapshot


class HealthyAdmin:
    def command(self, command):
        assert command == "ping"
        return {"ok": 1}


class HealthyClient:
    admin = HealthyAdmin()


class UnhealthyAdmin:
    def command(self, command):
        raise RuntimeError("mongo unavailable")


class UnhealthyClient:
    admin = UnhealthyAdmin()


def test_health_snapshot_reports_ok_when_mongo_ping_succeeds(monkeypatch):
    monkeypatch.setenv("APP_VERSION", "test-version")

    status, body = HealthSnapshot(HealthyClient()).build()

    assert status == HTTPStatus.OK
    assert body["status"] == "ok"
    assert body["version"] == "test-version"
    assert body["checks"] == {"mongo": True}
    assert {"cpu_percent", "mem_bytes", "mem_percent"} <= body["resources"].keys()


def test_health_snapshot_reports_503_when_mongo_ping_fails():
    status, body = HealthSnapshot(UnhealthyClient()).build()

    assert status == HTTPStatus.SERVICE_UNAVAILABLE
    assert body["status"] == "unhealthy"
    assert body["checks"] == {"mongo": False}
