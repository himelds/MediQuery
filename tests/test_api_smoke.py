"""
Smoke tests for the HTTP API:
- /health  — liveness + index population
- /collections/{role}  — role-to-collections mapping is reachable from outside
"""


class TestHealth:
    def test_health_returns_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"]
        assert isinstance(body["collections"], dict)

    def test_health_reports_all_six_collections(self, client):
        # If indexing was complete, /health should mention each named collection.
        response = client.get("/health")
        collections = response.json()["collections"]
        expected = {"medical", "clinical", "nursing", "billing", "equipment", "general"}
        # Every expected collection should appear; extras are allowed.
        assert expected.issubset(set(collections))

    def test_health_collection_counts_are_non_negative_integers(self, client):
        response = client.get("/health")
        for name, count in response.json()["collections"].items():
            assert isinstance(count, int), f"{name} count is {type(count)}"
            assert count >= 0, f"{name} count is negative: {count}"


class TestCollectionsForRole:
    def test_doctor_can_list_own_collections(self, client, doctor_token):
        response = client.get(
            "/collections/doctor",
            headers={"Authorization": f"Bearer {doctor_token}"},
        )
        assert response.status_code == 200
        # The doctor-allowed collections should appear in the response.
        text = str(response.json()).lower()
        for collection in ["medical", "clinical", "nursing", "general"]:
            assert collection in text, f"'{collection}' missing from doctor response"

    def test_unauthenticated_request_rejected(self, client):
        response = client.get("/collections/doctor")
        assert response.status_code == 401
