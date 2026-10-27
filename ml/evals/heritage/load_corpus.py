"""Import private originals through authenticated official source intake APIs.

No SQL writes, direct segment insertion, model inference or generation calls.
Run against an isolated deployment before the authorized main deployment.
"""

import argparse
import hashlib
import json
import os
import tempfile
import time
from pathlib import Path
from urllib.parse import urlsplit

import httpx

RIGHTS_NOTE = (
    "Owner authorized supplied documents for this internal application and model workflow. "
    "Preserve source attribution and historical/regional context. This authorization is "
    "not a claim of public licensing or expert cultural validation."
)
APPROVAL_REASON = (
    "Owner requested importing the supplied corpus for internal retrieval and application/model "
    "use. Original identity and extraction are verified technically; cultural claims still "
    "require source context. Sensitivity clearance is limited to this internal search corpus, "
    "not an expert endorsement of future generated uses."
)


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_receipts(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=".intake-", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump({"sources": records}, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def request(client: httpx.Client, method: str, path: str, **kwargs) -> httpx.Response:
    response = client.request(method, path, **kwargs)
    if not response.is_success:
        # Never dump response bodies, uploaded text, cookies or credentials.
        raise RuntimeError(f"Source API {method} {path} returned {response.status_code}")
    return response


def run(args) -> dict:
    parsed = urlsplit(args.base_url)
    if (
        parsed.scheme not in {"http", "https"}
        or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise ValueError("Use a loopback deployment base URL without credentials or path")
    full_inventory = read_json(args.store / "inventory.json")
    inventory = [item for item in full_inventory if item["format"] in args.formats]
    deferred = len(full_inventory) - len(inventory)
    metadata = read_json(args.metadata)
    metadata = metadata["sources"] if isinstance(metadata, dict) else metadata
    by_id = {item["source_id"]: item for item in metadata}
    if len(by_id) != len(metadata) or not {item["source_id"] for item in inventory} <= set(by_id):
        raise ValueError("Metadata must identify each selected private inventory source once")
    # Validate every input before the first server mutation.
    for item in inventory:
        path = Path(item["path"])
        if hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError(f"Original hash mismatch for {item['source_id']}")
        meta = by_id[item["source_id"]]
        evidence = urlsplit(meta.get("evidence_url", meta["origin_url"]))
        if (
            evidence.scheme != "https"
            or not evidence.netloc
            or evidence.username
            or evidence.password
        ):
            raise ValueError(f"HTTPS evidence_url required for {item['source_id']}")
        if item["format"] != "pdf":
            raise ValueError("Only inventoried PDF originals are supported")
    credentials = read_json(args.credentials)
    old_receipts = read_json(args.output)["sources"] if args.output.exists() else []
    old_by_id = {row["corpus_source_id"]: row for row in old_receipts}
    records = []
    uploaded = reused = 0
    origin = args.base_url.rstrip("/")
    with httpx.Client(base_url=origin, timeout=120, headers={"Origin": origin}) as client:
        login = request(
            client,
            "POST",
            "/api/v1/auth/login",
            json={
                "username": credentials["username"],
                "password": credentials["password"],
            },
        ).json()
        client.headers["X-CSRF-Token"] = login["csrf_token"]
        existing = request(client, "GET", "/api/v1/admin/sources", params={"limit": 100}).json()
        if len(existing) >= 100:
            raise ValueError(
                "Admin inventory is saturated; pagination is required for safe deduplication"
            )
        details = [
            request(client, "GET", f"/api/v1/admin/revisions/{row['revision_id']}").json()
            for row in existing
        ]
        hashes = {}
        for detail in details:
            hashes.setdefault(detail["sha256"], []).append(detail)
        for item in inventory:
            corpus_id = item["source_id"]
            meta = by_id[corpus_id]
            candidates = hashes.get(item["sha256"], [])
            previous = old_by_id.get(corpus_id)
            if previous and previous.get("base_url") == origin:
                # A receipt may reference a revision outside the inventory window.
                if not any(row["revision_id"] == previous["revision_id"] for row in candidates):
                    detail = request(
                        client, "GET", f"/api/v1/admin/revisions/{previous['revision_id']}"
                    ).json()
                    if detail["sha256"] != item["sha256"]:
                        raise ValueError("Receipt revision hash changed")
                    candidates.append(detail)
            if len(candidates) > 1:
                raise ValueError(
                    f"Multiple existing revisions match {corpus_id}; resolve explicitly"
                )
            if candidates:
                detail = candidates[0]
                if detail["origin_url"] != meta["origin_url"]:
                    raise ValueError(f"Existing original has different provenance for {corpus_id}")
                if detail["decision"] == "revoke":
                    raise ValueError(f"Refusing to reapprove revoked source {corpus_id}")
                revision_id, source_id = detail["revision_id"], detail["source_id"]
                reused += 1
            else:
                form = {
                    "origin_url": meta["origin_url"],
                    "title": meta["title"],
                    "rights_note": RIGHTS_NOTE,
                }
                if meta.get("creator"):
                    form["creator"] = meta["creator"]
                tags = meta.get("tags", [])
                if tags:
                    form["tags"] = [f"{tag['kind']}:{tag['value']}" for tag in tags]
                mime = "application/pdf"
                with Path(item["path"]).open("rb") as stream:
                    intake = request(
                        client,
                        "POST",
                        "/api/v1/admin/sources",
                        data=form,
                        files={"file": (Path(item["path"]).name, stream, mime)},
                    ).json()
                revision_id, source_id = intake["revision_id"], intake["source_id"]
                uploaded += 1
            receipt = {
                "corpus_source_id": corpus_id,
                "base_url": origin,
                "source_id": source_id,
                "revision_id": revision_id,
                "sha256": item["sha256"],
                "state": "intake",
            }
            records.append(receipt)
            # Preserve recoverability if the worker or a later approval fails.
            save_receipts(
                args.output,
                records
                + [
                    row
                    for row in old_receipts
                    if row["corpus_source_id"] not in {r["corpus_source_id"] for r in records}
                ],
            )
            deadline = time.monotonic() + args.timeout
            while True:
                detail = request(client, "GET", f"/api/v1/admin/revisions/{revision_id}").json()
                if detail["status"] == "review_pending":
                    break
                if detail["status"] == "failed":
                    raise RuntimeError(f"Extraction failed for {corpus_id}: {detail['error_code']}")
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"Extraction did not finish for {corpus_id}")
                time.sleep(args.poll_interval)
            if detail["sha256"] != item["sha256"] or not detail["segments"]:
                raise ValueError(f"Original identity or extraction mismatch for {corpus_id}")
            original = request(client, "GET", f"/api/v1/admin/revisions/{revision_id}/original")
            if hashlib.sha256(original.content).hexdigest() != item["sha256"]:
                raise ValueError(f"API original hash mismatch for {corpus_id}")
            if detail["decision"] != "approve":
                request(
                    client,
                    "POST",
                    f"/api/v1/admin/revisions/{revision_id}/approve",
                    json={
                        "reason": APPROVAL_REASON,
                        "evidence_url": meta.get("evidence_url", meta["origin_url"]),
                        "user_text": True,
                        "original_file": True,
                        "provider_transfer": True,
                        "sensitivity_cleared": True,
                    },
                )
            verified = request(client, "GET", f"/api/v1/admin/revisions/{revision_id}").json()
            if verified["decision"] != "approve":
                raise ValueError(f"Approval verification failed for {corpus_id}")
            receipt.update(
                state="approved", segments=len(detail["segments"]), original_hash_verified=True
            )
            hashes[item["sha256"]] = [verified]
            save_receipts(
                args.output,
                records
                + [
                    row
                    for row in old_receipts
                    if row["corpus_source_id"] not in {r["corpus_source_id"] for r in records}
                ],
            )
    save_receipts(args.output, records)
    return {
        "sources": len(records),
        "deferred": deferred,
        "uploaded": uploaded,
        "reused": reused,
        "approved": sum(row["state"] == "approved" for row in records),
        "original_hashes_verified": sum(
            row.get("original_hash_verified", False) for row in records
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--formats", nargs="+", choices=["pdf"], default=["pdf"])
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--credentials", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=1800)
    parser.add_argument("--poll-interval", type=float, default=2)
    args = parser.parse_args()
    if args.timeout <= 0 or not 0 < args.poll_interval <= 60:
        parser.error(
            "Timeout and poll interval must be positive; poll interval must be at most 60s"
        )
    print(json.dumps(run(args)))


if __name__ == "__main__":
    main()
