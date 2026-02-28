import os
import time
import requests
import random
import uuid

API = "http://127.0.0.1:8000"
WORKER_ID = os.getenv("WORKER_ID", str(uuid.uuid4())[:8])


def safe_post(url: str, **kwargs):
    """
    Helper to POST with basic error handling.
    Returns the response object, or None if the request itself failed.
    """
    try:
        # Provide a default timeout if caller didn't pass one
        kwargs.setdefault("timeout", 5)
        return requests.post(url, **kwargs)
    except Exception as exc:
        print(f"[worker] POST {url} failed: {exc}", flush=True)
        return None

def safe_get(url: str, **kwargs):
    try:
        kwargs.setdefault("timeout", 5)
        return requests.get(url, **kwargs)
    except Exception as exc:
        print(f"[worker] GET {url} failed: {exc}", flush=True)
        return None

def reconcile():
    resp = safe_post(f"{API}/system/reconcile")
    if resp is None:
        return
    if resp.status_code != 200:
        print(f"[worker] reconcile failed: {resp.status_code} {resp.text}", flush=True)

def main():
    print("Worker started. Watching for queued jobs...", flush=True)

    while True:
        try:
            resp = safe_get(f"{API}/jobs")
            if resp is None:
                print("[worker] Could not fetch jobs", flush=True)
                time.sleep(2)
                continue

            try:
                jobs = resp.json()
            except Exception as exc:
                print(f"[worker] Invalid /jobs response: {exc}", flush=True)
                time.sleep(2)
                continue

            queued = [j for j in jobs if j.get("status") == "queued"]

            if not queued:
                reconcile()
                time.sleep(2)
                continue

            job = queued[0]
            job_id = job["id"]

            # lease
            lease_resp = safe_post(
                f"{API}/jobs/{job_id}/lease",
                json={"worker_id": WORKER_ID, "lease_seconds": 30}
            )
            if lease_resp is None or lease_resp.status_code != 200:
                print(f"[worker] Could not lease job {job_id}: {lease_resp.text if lease_resp else 'no response'}", flush=True)
                continue

            # start
            r = requests.post(f"{API}/jobs/{job_id}/start", timeout=5)
            if r.status_code != 200:
                print(f"Could not start job {job_id}: {r.text}", flush=True)
                time.sleep(1)
                continue

            print(f"Running job {job_id} (type={job['type']})", flush=True)
            
            # START TIMER HERE
            start_time = time.time()
          
            time.sleep(3)

            # simulate work
            time.sleep(2)

            # fail some jobs intentionally
            should_fail = random.random() < 0.3  # 30% failure rate
            if should_fail:
                runtime_ms = int((time.time() - start_time) * 1000)
                safe_post(
                    f"{API}/jobs/{job_id}/telemetry",
                    json={"runtime_ms": runtime_ms, "note": "failed-run"}
                )

                err = "Simulated failure during execution"
                requests.post(f"{API}/jobs/{job_id}/fail", json={"error": err}, timeout=5)
                print(f"Failed job {job_id} (will retry if attempts left)", flush=True)
                
                reconcile()
                continue

            runtime_ms = int((time.time() - start_time) * 1000)

            safe_post(
                f"{API}/jobs/{job_id}/telemetry",
                json={"runtime_ms": runtime_ms, "note": "success-run"}
            )


            # mark job as completed
            r = requests.post(f"{API}/jobs/{job_id}/complete", timeout=5)
            if r.status_code == 200:
                print(f"Completed job {job_id}", flush=True)
            else:
                print(f"Could not complete job {job_id}: {r.text}", flush=True)

            reconcile()

        except Exception as e:
            print("Worker error:", e, flush=True)

        time.sleep(1)

if __name__ == "__main__":
    main()