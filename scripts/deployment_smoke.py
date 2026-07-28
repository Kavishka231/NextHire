#!/usr/bin/env python3
"""Destructive end-to-end smoke test for a staging or production-like NextHire."""

from __future__ import annotations

import argparse
import atexit
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar


class SmokeFailure(RuntimeError):
    pass


class Client:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.cookies = CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookies)
        )
        self.access_token: str | None = None

    def request(
        self,
        method: str,
        path: str,
        payload: dict | None = None,
        expected: int | tuple[int, ...] = 200,
    ):
        expected_codes = (expected,) if isinstance(expected, int) else expected
        body = None if payload is None else json.dumps(payload).encode()
        headers = {"Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        request = urllib.request.Request(
            f"{self.base_url}{path}", data=body, headers=headers, method=method
        )
        try:
            with self.opener.open(request, timeout=20) as response:
                status = response.status
                raw = response.read()
        except urllib.error.HTTPError as exc:
            status = exc.code
            raw = exc.read()
        except (urllib.error.URLError, TimeoutError, ssl.SSLError) as exc:
            raise SmokeFailure(f"{method} {path} could not connect: {exc}") from exc
        decoded = json.loads(raw) if raw else None
        if status not in expected_codes:
            raise SmokeFailure(
                f"{method} {path} returned {status}, expected {expected_codes}: "
                f"{decoded}"
            )
        return decoded

    def login(self, email: str, password: str):
        result = self.request(
            "POST", "/api/v1/auth/login", {"email": email, "password": password}
        )
        self.access_token = result["access_token"]
        return result


def step(label: str):
    print(f"[PASS] {label}")


def run(args: argparse.Namespace) -> None:
    suffix = str(int(time.time()))
    candidate_email = f"smoke-candidate-{suffix}@{args.test_email_domain}"
    company_email = f"smoke-company-{suffix}@{args.test_email_domain}"
    initial_password = f"Smoke-{suffix}-A!"
    changed_password = f"Smoke-{suffix}-B!"
    created_user_ids: list[int] = []
    created_job_id: int | None = None
    company_user_id: int | None = None

    public = Client(args.base_url)
    admin = Client(args.base_url)
    admin.login(args.admin_email, args.admin_password)
    company = Client(args.base_url)

    def cleanup() -> None:
        nonlocal created_job_id
        for user_id in [
            item for item in created_user_ids.copy() if item != company_user_id
        ]:
            try:
                admin.request("DELETE", f"/api/v1/admin/users/{user_id}")
                created_user_ids.remove(user_id)
            except SmokeFailure as exc:
                print(f"[WARN] user {user_id} cleanup failed: {exc}", file=sys.stderr)
        if created_job_id is not None:
            try:
                company.request("DELETE", f"/api/v1/jobs/company/{created_job_id}")
                created_job_id = None
            except SmokeFailure as exc:
                print(f"[WARN] job cleanup failed: {exc}", file=sys.stderr)
        for user_id in created_user_ids.copy():
            try:
                admin.request("DELETE", f"/api/v1/admin/users/{user_id}")
                created_user_ids.remove(user_id)
            except SmokeFailure as exc:
                print(f"[WARN] user {user_id} cleanup failed: {exc}", file=sys.stderr)
        if created_job_id is not None:
            print(f"[WARN] cleanup required for job id {created_job_id}", file=sys.stderr)
        if created_user_ids:
            print(
                f"[WARN] cleanup required for user ids {created_user_ids}",
                file=sys.stderr,
            )

    atexit.register(cleanup)
    public.request("GET", "/health")
    public.request("GET", "/ready")
    step("liveness and dependency readiness")

    candidate = Client(args.base_url)
    candidate_user = candidate.request(
        "POST",
        "/api/v1/auth/register",
        {
            "email": candidate_email,
            "full_name": "Deployment Smoke Candidate",
            "password": initial_password,
        },
        expected=201,
    )
    created_user_ids.append(candidate_user["id"])
    candidate.login(candidate_email, initial_password)
    candidate.request("GET", "/api/v1/auth/me")
    step("candidate registration and login")

    old_refresh = next(
        (
            cookie.value
            for cookie in candidate.cookies
            if cookie.name == args.refresh_cookie_name
        ),
        None,
    )
    candidate.request("POST", "/api/v1/auth/refresh")
    rotated_refresh = next(
        (
            cookie.value
            for cookie in candidate.cookies
            if cookie.name == args.refresh_cookie_name
        ),
        None,
    )
    if not old_refresh or not rotated_refresh or old_refresh == rotated_refresh:
        raise SmokeFailure("refresh cookie was not rotated")
    step("refresh-token rotation")

    company_user = company.request(
        "POST",
        "/api/v1/auth/register",
        {
            "email": company_email,
            "full_name": "Deployment Smoke Employer",
            "password": initial_password,
            "account_type": "company",
            "company_name": "NextHire Smoke Company",
            "company_website": "https://example.test",
            "company_description": "Temporary deployment verification account",
        },
        expected=201,
    )
    company_user_id = company_user["id"]
    created_user_ids.append(company_user["id"])
    company.login(company_email, initial_password)

    admin.request("GET", "/api/v1/admin/summary")
    users = admin.request("GET", "/api/v1/admin/users")
    if not any(user["id"] == candidate_user["id"] for user in users):
        raise SmokeFailure("temporary candidate was not visible to the administrator")
    admin.request(
        "PATCH",
        f"/api/v1/admin/companies/{company_user['id']}/approval",
        {"approved": True},
    )
    step("admin user listing and employer approval")

    job = company.request(
        "POST",
        "/api/v1/jobs/company",
        {
            "title": f"Deployment Smoke Job {suffix}",
            "location": "Remote",
            "description": "Temporary end-to-end deployment smoke test",
            "application_email": company_email,
        },
    )
    created_job_id = job["id"]
    company.request(
        "PUT",
        f"/api/v1/jobs/company/{created_job_id}",
        {"title": f"Updated Deployment Smoke Job {suffix}"},
    )
    company_jobs = company.request("GET", "/api/v1/jobs/company/mine")
    if not any(item["id"] == created_job_id for item in company_jobs):
        raise SmokeFailure("created employer job was not returned")
    step("employer job create, update, and listing")

    search = candidate.request(
        "GET",
        "/api/v1/search/jobs?"
        + urllib.parse.urlencode({"keywords": "Deployment Smoke Job"}),
    )
    if not any(item["external_id"] == job["external_id"] for item in search["jobs"]):
        raise SmokeFailure("created employer job was not searchable")
    step("job search")

    saved = candidate.request(
        "POST", "/api/v1/saved-jobs", {"external_id": job["external_id"]}
    )
    note = candidate.request(
        "POST",
        "/api/v1/notes",
        {"saved_job_id": saved["id"], "content": "Deployment smoke note"},
        expected=201,
    )
    candidate.request(
        "PUT", f"/api/v1/notes/{note['id']}", {"content": "Updated smoke note"}
    )
    candidate.request(
        "PATCH", f"/api/v1/saved-jobs/{saved['id']}/status", {"status": "applied"}
    )
    step("saved jobs, notes, and board status")

    application = candidate.request(
        "POST",
        "/api/v1/applications",
        {
            "external_id": job["external_id"],
            "use_profile": False,
            "applicant_name": "Deployment Smoke Candidate",
            "applicant_email": candidate_email,
            "cover_letter": "Temporary deployment smoke application.",
        },
    )
    employer_applications = company.request("GET", "/api/v1/applications/company")
    if not any(item["id"] == application["id"] for item in employer_applications):
        raise SmokeFailure("submitted application was not visible to employer")
    company.request(
        "PATCH",
        f"/api/v1/applications/{application['id']}/status",
        {"status": "interview"},
    )
    step("application submission and employer status update")

    candidate.request(
        "PUT",
        "/api/v1/auth/change-password",
        {"current_password": initial_password, "new_password": changed_password},
    )
    candidate.request("POST", "/api/v1/auth/refresh", expected=401)
    candidate.login(candidate_email, changed_password)
    step("password change and refresh-session revocation")

    candidate.request(
        "POST", "/api/v1/auth/forgot-password", {"email": candidate_email}
    )
    step("password-reset email queued; delivery and reset link require manual evidence")

    candidate.request("POST", "/api/v1/auth/logout")
    candidate.request("POST", "/api/v1/auth/refresh", expected=401)
    step("logout and refresh-session revocation")

    cleanup()
    step("temporary records cleaned up")

    print("\nAutomated deployment smoke tests passed.")
    print("Complete the email, reminder, restart, and browser checks in the runbook.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-url",
        default=os.getenv("SMOKE_BASE_URL"),
        help="HTTPS staging/application URL (or SMOKE_BASE_URL)",
    )
    parser.add_argument(
        "--admin-email",
        default=os.getenv("SMOKE_ADMIN_EMAIL"),
        help="Dedicated administrator email (or SMOKE_ADMIN_EMAIL)",
    )
    parser.add_argument(
        "--admin-password",
        default=os.getenv("SMOKE_ADMIN_PASSWORD"),
        help="Dedicated administrator password (prefer SMOKE_ADMIN_PASSWORD)",
    )
    parser.add_argument(
        "--refresh-cookie-name",
        default="nexthire_refresh",
        help="Refresh-cookie name configured by the deployment",
    )
    parser.add_argument(
        "--test-email-domain",
        default=os.getenv("SMOKE_EMAIL_DOMAIN"),
        help="Controlled domain that accepts generated smoke-test addresses",
    )
    parser.add_argument(
        "--confirm-write-tests",
        action="store_true",
        help="Confirm temporary users, jobs, applications, and email will be created",
    )
    args = parser.parse_args()
    if not args.confirm_write_tests:
        parser.error("--confirm-write-tests is required because this suite changes data")
    missing = [
        name
        for name, value in (
            ("SMOKE_BASE_URL/--base-url", args.base_url),
            ("SMOKE_ADMIN_EMAIL/--admin-email", args.admin_email),
            ("SMOKE_ADMIN_PASSWORD/--admin-password", args.admin_password),
            ("SMOKE_EMAIL_DOMAIN/--test-email-domain", args.test_email_domain),
        )
        if not value
    ]
    if missing:
        parser.error("missing required configuration: " + ", ".join(missing))
    parsed = urllib.parse.urlparse(args.base_url)
    if parsed.scheme != "https" and parsed.hostname not in {"localhost", "127.0.0.1"}:
        parser.error("non-local smoke targets must use HTTPS")
    return args


if __name__ == "__main__":
    try:
        run(parse_args())
    except SmokeFailure as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        raise SystemExit(1)
