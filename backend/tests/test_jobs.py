import pytest

SEARCH_URL = "/api/v1/search/jobs"
CATS_URL   = "/api/v1/search/categories"


def test_search_allows_public_browsing(client):
    res = client.get(SEARCH_URL, params={"keywords": "python"})
    assert res.status_code == 200
    assert "jobs" in res.json()


def test_search_returns_results(client, auth_headers):
    res = client.get(SEARCH_URL, params={"keywords": "developer"}, headers=auth_headers)
    assert res.status_code == 200
    body = res.json()
    assert "jobs" in body
    assert "total" in body
    assert isinstance(body["jobs"], list)


def test_search_pagination(client, auth_headers):
    res = client.get(SEARCH_URL, params={"keywords": "developer", "page": 1, "results_per_page": 5}, headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["results_per_page"] == 5


def test_public_jobs_use_consistent_pagination(client):
    client.get(SEARCH_URL, params={"keywords": "team", "results_per_page": 10})

    res = client.get("/api/v1/jobs", params={"page": 2, "page_size": 3})

    assert res.status_code == 200
    assert set(res.json()) == {"items", "page", "page_size", "total"}
    assert res.json()["page"] == 2
    assert res.json()["page_size"] == 3
    assert res.json()["total"] == 10
    assert len(res.json()["items"]) == 3


def test_search_with_location(client, auth_headers):
    res = client.get(SEARCH_URL, params={"keywords": "python", "location": "London"}, headers=auth_headers)
    assert res.status_code == 200


def test_search_with_salary_filter(client, auth_headers):
    res = client.get(SEARCH_URL, params={"keywords": "engineer", "salary_min": 50000}, headers=auth_headers)
    assert res.status_code == 200


def test_search_keywords_required(client, auth_headers):
    res = client.get(SEARCH_URL, headers=auth_headers)
    assert res.status_code == 422


def test_categories(client, auth_headers):
    res = client.get(CATS_URL, headers=auth_headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_saving_same_job_twice_returns_conflict(client, auth_headers):
    search = client.get(SEARCH_URL, params={"keywords": "developer"})
    external_id = search.json()["jobs"][0]["external_id"]

    first = client.post(
        "/api/v1/saved-jobs",
        json={"external_id": external_id},
        headers=auth_headers,
    )
    duplicate = client.post(
        "/api/v1/saved-jobs",
        json={"external_id": external_id},
        headers=auth_headers,
    )

    assert first.status_code == 200
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "Job already saved"


def test_saved_jobs_are_paginated(client, auth_headers):
    search = client.get(
        SEARCH_URL,
        params={"keywords": "team", "results_per_page": 5},
    ).json()
    for job in search["jobs"]:
        response = client.post(
            "/api/v1/saved-jobs",
            json={"external_id": job["external_id"]},
            headers=auth_headers,
        )
        assert response.status_code == 200

    res = client.get(
        "/api/v1/saved-jobs?page=2&page_size=2",
        headers=auth_headers,
    )

    assert res.status_code == 200
    assert res.json()["page"] == 2
    assert res.json()["page_size"] == 2
    assert res.json()["total"] == 5
    assert len(res.json()["items"]) == 2
