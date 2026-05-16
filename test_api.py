"""
test_api.py — Integration tests for the Notes REST API
Usage:  python test_api.py
Requires: pip install requests
"""

import json
import sys
import uuid

import requests

BASE = "http://127.0.0.1:8000"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

passed = 0
failed = 0
total  = 13


def ok(label: str) -> None:
    global passed
    passed += 1
    print(f"  ✅ PASS  [{label}]")


def fail(label: str, reason: str) -> None:
    global failed
    failed += 1
    print(f"  ❌ FAIL  [{label}]")
    print(f"          Reason: {reason}")
    _summary()
    sys.exit(1)


def _summary() -> None:
    total_run = passed + failed
    print()
    print("─" * 50)
    print(f"  Results: {passed}/{total_run} tests passed")
    print("─" * 50)


def check(label: str, response: requests.Response,
          expected_status: int, *,
          required_keys: list[str] | None = None,
          check_fn=None) -> dict:
    """
    Assert HTTP status, optionally check keys / a custom function.
    Returns parsed JSON body on success, calls fail() (which exits) on error.
    """
    if response.status_code != expected_status:
        try:
            body = response.json()
        except Exception:
            body = response.text
        fail(label, f"Expected HTTP {expected_status}, got {response.status_code}. Body: {body}")

    try:
        body = response.json()
    except Exception:
        body = {}

    if required_keys:
        missing = [k for k in required_keys if k not in body]
        if missing:
            fail(label, f"Response missing keys: {missing}. Body: {body}")

    if check_fn:
        error = check_fn(body)
        if error:
            fail(label, error)

    ok(label)
    return body


# ---------------------------------------------------------------------------
# Test data — random emails so re-runs never clash
# ---------------------------------------------------------------------------
uid1   = uuid.uuid4().hex[:8]
uid2   = uuid.uuid4().hex[:8]
EMAIL1 = f"user1_{uid1}@test.com"
EMAIL2 = f"user2_{uid2}@test.com"
PASS1  = "password123"
PASS2  = "password456"

token1   = None
token2   = None
note_id  = None


def auth1() -> dict:
    return {"Authorization": f"Bearer {token1}"}


def auth2() -> dict:
    return {"Authorization": f"Bearer {token2}"}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
print()
print("=" * 50)
print("  Notes API — Integration Test Suite")
print(f"  Base URL : {BASE}")
print(f"  User 1   : {EMAIL1}")
print(f"  User 2   : {EMAIL2}")
print("=" * 50)
print()

# ── 1. POST /auth/register (user 1) ─────────────────────────────────────────
r = requests.post(f"{BASE}/auth/register", json={"email": EMAIL1, "password": PASS1})
check(
    "POST /auth/register (user 1)",
    r, 201,
    check_fn=lambda b: None if b.get("message") == "User registered successfully"
                       else f"Unexpected message: {b.get('message')}",
)

# ── 2. POST /auth/login (user 1) ─────────────────────────────────────────────
r = requests.post(f"{BASE}/auth/login", json={"email": EMAIL1, "password": PASS1})
body = check("POST /auth/login (user 1)", r, 200, required_keys=["access_token"])
token1 = body["access_token"]

# ── 3. POST /notes ───────────────────────────────────────────────────────────
r = requests.post(
    f"{BASE}/notes/",
    json={"title": "My First Note", "content": "Hello from test_api.py"},
    headers=auth1(),
)
body = check(
    "POST /notes",
    r, 201,
    required_keys=["id", "title", "content", "pinned", "owner_id", "created_at", "updated_at"],
    check_fn=lambda b: None if b["title"] == "My First Note"
                       else f"title mismatch: {b['title']}",
)
note_id = body["id"]

# ── 4. GET /notes ────────────────────────────────────────────────────────────
r = requests.get(f"{BASE}/notes/", headers=auth1())
body = check("GET /notes", r, 200)
if not isinstance(body, list):
    fail("GET /notes", f"Expected a list, got: {type(body)}")
ids = [n["id"] for n in body]
if note_id not in ids:
    fail("GET /notes", f"Created note {note_id} not found in list: {ids}")
ok("GET /notes — created note present in list")

# ── 5. GET /notes/{id} ───────────────────────────────────────────────────────
r = requests.get(f"{BASE}/notes/{note_id}", headers=auth1())
check(
    "GET /notes/{id}",
    r, 200,
    check_fn=lambda b: None if b["id"] == note_id
                       else f"id mismatch: {b['id']}",
)

# ── 6. PUT /notes/{id} ───────────────────────────────────────────────────────
r = requests.put(
    f"{BASE}/notes/{note_id}",
    json={"title": "Updated Title", "content": "Updated content"},
    headers=auth1(),
)
check(
    "PUT /notes/{id}",
    r, 200,
    check_fn=lambda b: (
        None if b["title"] == "Updated Title" and b["content"] == "Updated content"
        else f"Update not reflected — title={b.get('title')}, content={b.get('content')}"
    ),
)

# ── 7. PATCH /notes/{id}/pin ─────────────────────────────────────────────────
r = requests.patch(f"{BASE}/notes/{note_id}/pin", headers=auth1())
check(
    "PATCH /notes/{id}/pin",
    r, 200,
    check_fn=lambda b: None if b.get("pinned") is True
                       else f"Expected pinned=True, got: {b.get('pinned')}",
)

# ── 8. Register + login user 2 ───────────────────────────────────────────────
r = requests.post(f"{BASE}/auth/register", json={"email": EMAIL2, "password": PASS2})
check("POST /auth/register (user 2)", r, 201)

r = requests.post(f"{BASE}/auth/login", json={"email": EMAIL2, "password": PASS2})
body = check("POST /auth/login (user 2)", r, 200, required_keys=["access_token"])
token2 = body["access_token"]

# ── 9. POST /notes/{id}/share ────────────────────────────────────────────────
r = requests.post(
    f"{BASE}/notes/{note_id}/share",
    json={"shared_with_email": EMAIL2},
    headers=auth1(),
)
check(
    "POST /notes/{id}/share",
    r, 200,
    check_fn=lambda b: None if b.get("message") == "Note shared successfully"
                       else f"Unexpected message: {b.get('message')}",
)

# ── 10. GET /notes/{id} as user 2 (shared access) ───────────────────────────
r = requests.get(f"{BASE}/notes/{note_id}", headers=auth2())
check(
    "GET /notes/{id} — shared user access",
    r, 200,
    check_fn=lambda b: None if b["id"] == note_id
                       else f"id mismatch: {b['id']}",
)

# ── 11. DELETE /notes/{id} (owner) ───────────────────────────────────────────
r = requests.delete(f"{BASE}/notes/{note_id}", headers=auth1())
if r.status_code != 204:
    fail("DELETE /notes/{id}", f"Expected 204, got {r.status_code}. Body: {r.text}")
ok("DELETE /notes/{id}")

# Verify it's actually gone
r = requests.get(f"{BASE}/notes/{note_id}", headers=auth1())
if r.status_code != 404:
    fail("DELETE /notes/{id} — verify gone", f"Expected 404 after delete, got {r.status_code}")
ok("DELETE /notes/{id} — confirmed 404 after deletion")

# ── 12. GET /about ───────────────────────────────────────────────────────────
r = requests.get(f"{BASE}/about")
check(
    "GET /about",
    r, 200,
    required_keys=["name", "email"],
    check_fn=lambda b: (
        None if b.get("name") and b.get("email")
        else f"name or email is empty — got name={b.get('name')}, email={b.get('email')}"
    ),
)

# ── 13. GET /openapi.json ────────────────────────────────────────────────────
r = requests.get(f"{BASE}/openapi.json")
check(
    "GET /openapi.json",
    r, 200,
    required_keys=["openapi", "info", "paths"],
)

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
_summary()
