import pytest

NOTES_URL = "/api/v1/notes"
STATS_URL = "/api/v1/stats"


# ── Notes ──────────────────────────────────────────────────────────────────────

def test_add_note(client, auth_headers, saved_job_id):
    res = client.post(NOTES_URL, json={"saved_job_id": saved_job_id, "content": "Great role!"}, headers=auth_headers)
    assert res.status_code == 201
    assert res.json()["content"] == "Great role!"
    assert res.json()["saved_job_id"] == saved_job_id


def test_add_note_empty_content(client, auth_headers, saved_job_id):
    res = client.post(NOTES_URL, json={"saved_job_id": saved_job_id, "content": "   "}, headers=auth_headers)
    assert res.status_code == 422


def test_list_notes(client, auth_headers, saved_job_id):
    client.post(NOTES_URL, json={"saved_job_id": saved_job_id, "content": "Note 1"}, headers=auth_headers)
    client.post(NOTES_URL, json={"saved_job_id": saved_job_id, "content": "Note 2"}, headers=auth_headers)
    res = client.get(f"{NOTES_URL}/job/{saved_job_id}", headers=auth_headers)
    assert res.status_code == 200
    assert len(res.json()) == 2


def test_update_note(client, auth_headers, saved_job_id):
    note = client.post(NOTES_URL, json={"saved_job_id": saved_job_id, "content": "Old"}, headers=auth_headers).json()
    res  = client.put(f"{NOTES_URL}/{note['id']}", json={"content": "Updated"}, headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["content"] == "Updated"


def test_delete_note(client, auth_headers, saved_job_id):
    note = client.post(NOTES_URL, json={"saved_job_id": saved_job_id, "content": "Delete me"}, headers=auth_headers).json()
    res  = client.delete(f"{NOTES_URL}/{note['id']}", headers=auth_headers)
    assert res.status_code == 204
    notes = client.get(f"{NOTES_URL}/job/{saved_job_id}", headers=auth_headers).json()
    assert len(notes) == 0


def test_note_requires_auth(client, saved_job_id):
    res = client.get(f"{NOTES_URL}/job/{saved_job_id}")
    assert res.status_code == 401


def test_note_on_invalid_job(client, auth_headers):
    res = client.post(NOTES_URL, json={"saved_job_id": 9999, "content": "test"}, headers=auth_headers)
    assert res.status_code == 404


# ── Stats ──────────────────────────────────────────────────────────────────────

def test_stats_empty(client, auth_headers):
    res = client.get(STATS_URL, headers=auth_headers)
    assert res.status_code == 200
    body = res.json()
    assert body["total_saved"]   == 0
    assert body["total_applied"] == 0
    assert "status_counts"   in body
    assert "weekly_activity" in body
    assert "top_companies"   in body


def test_stats_with_data(client, auth_headers, saved_job_id):
    # Move to applied
    client.patch(f"/api/v1/saved-jobs/{saved_job_id}/status", json={"status": "applied"}, headers=auth_headers)
    res = client.get(STATS_URL, headers=auth_headers)
    assert res.status_code == 200
    body = res.json()
    assert body["total_applied"] == 1


def test_stats_requires_auth(client):
    res = client.get(STATS_URL)
    assert res.status_code == 401
