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
