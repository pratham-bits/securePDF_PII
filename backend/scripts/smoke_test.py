import sys
import time
import uuid
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8000/api"
SAMPLES = Path(__file__).resolve().parents[2] / "samples"
OUT_DIR = Path(__file__).resolve().parents[1] / "storage"
PASSWORD = "smoke-test-password-123"


def fail(message: str):
    print(f"FAIL: {message}")
    sys.exit(1)


def expect(response, code: int, what: str):
    if response.status_code != code:
        fail(f"{what}: expected {code}, got {response.status_code} ({response.text[:200]})")
    print(f"ok   {what} -> {response.status_code}")
    return response


def wait_for(client, document_id: str, wanted: str, timeout: int = 240) -> dict:
    start = time.time()
    while time.time() - start < timeout:
        document = client.get(f"/documents/{document_id}").json()
        status = document.get("status")
        if status == wanted:
            return document
        if status == "failed" or (status == "ready" and document.get("error_code")):
            fail(f"ended as {status} with error_code={document.get('error_code')}")
        time.sleep(1)
    fail(f"timed out waiting for status {wanted}")


def run(client, sample_name: str):
    print(f"\n== {sample_name} ==")
    data = (SAMPLES / sample_name).read_bytes()
    files = {"file": ("x.pdf", data, "application/pdf")}
    document_id = expect(client.post("/documents", files=files), 201, "upload").json()["id"]

    expect(client.post(f"/documents/{document_id}/analyze"), 202, "analyze")
    wait_for(client, document_id, "ready")
    findings = expect(client.get(f"/documents/{document_id}/findings"), 200, "findings").json()
    print("     found:", sorted(f["entity_type"] for f in findings))

    mandatory = next((f for f in findings if f["tier"] == "mandatory"), None)
    if mandatory is None:
        fail("no mandatory finding was detected")
    url = f"/documents/{document_id}/findings/{mandatory['id']}"
    expect(
        client.patch(url, json={"decision": "keep"}),
        409,
        "keeping a mandatory item without confirmation is refused",
    )

    expect(client.post(f"/documents/{document_id}/redact"), 202, "redact")
    wait_for(client, document_id, "redacted")
    response = expect(client.get(f"/documents/{document_id}/download"), 200, "download")
    out = OUT_DIR / f"smoke_{sample_name}"
    out.write_bytes(response.content)
    print(f"     saved {out}")

    expect(client.delete(f"/documents/{document_id}"), 204, "delete")
    expect(client.get(f"/documents/{document_id}"), 404, "deleted document is gone")


def main():
    email = f"smoke-{uuid.uuid4().hex[:8]}@example.com"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with httpx.Client(base_url=BASE, timeout=60) as client:
        creds = {"email": email, "password": PASSWORD}
        expect(client.post("/auth/register", json=creds), 201, "register")
        expect(client.post("/auth/login", json=creds), 200, "login")
        for sample in ("sample_digital_en.pdf", "sample_scanned_en.pdf"):
            run(client, sample)
    print("\nAll checks passed.")


main()