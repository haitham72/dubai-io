import httpx
import pytest


@pytest.mark.e2e
def test_docker_workers_consume_reserved_queues(stack):
    with httpx.Client(
        base_url=f"http://127.0.0.1:{stack.port('rabbitmq', 15672)}",
        auth=("guest", "guest"),
        trust_env=False,
    ) as management:
        for queue in ("mem.p0", "mem.p1", "mem.p3"):
            response = management.get(f"/api/queues/%2F/{queue}")
            response.raise_for_status()
            assert response.json()["consumers"] == 1, queue
            response = management.get(f"/api/queues/%2F/{queue}/bindings")
            response.raise_for_status()
            assert {(row["source"], row["routing_key"]) for row in response.json()} == {
                ("", queue), (queue, queue),
            }


@pytest.mark.e2e
def test_owner_written_after_health_read_is_visible_to_other_clients(stack):
    assert stack.api.get("/health").json()["ok"]
    owner = stack.owner()
    assert stack.rows("SELECT id FROM owners WHERE id = %s", (owner,)) == [{"id": owner}]
