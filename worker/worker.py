import time
import requests
import random           

API = "http://127.0.0.1:8000"

def main():
    print("Worker started. Watching for queued jobs...", flush=True)

    while True:
        try:
            jobs = requests.get(f"{API}/jobs", timeout=5).json()
            queued = [j for j in jobs if j["status"] == "queued"]

            if not queued:
                time.sleep(2)
                continue

            job = queued[0]
            job_id = job["id"]

            # start
            r = requests.post(f"{API}/jobs/{job_id}/start", timeout=5)
            if r.status_code != 200:
                print(f"Could not start job {job_id}: {r.text}", flush=True)
                time.sleep(1)
                continue

            print(f"Running job {job_id} (type={job['type']})", flush=True)
            time.sleep(3)

            # simulate work
            time.sleep(2)

            # fail some jobs intentionally
            should_fail = random.random() < 0.3  # 30% failure rate
            if should_fail:
                err = "Simulated failure during execution"
                requests.post(f"{API}/jobs/{job_id}/fail", json={"error": err}, timeout=5)
                print(f"Failed job {job_id} (will retry if attempts left)", flush=True)
                continue

            # mark job as completed
            r = requests.post(f"{API}/jobs/{job_id}/complete", timeout=5)
            if r.status_code == 200:
                print(f"Completed job {job_id}", flush=True)
            else:
                print(f"Could not complete job {job_id}: {r.text}", flush=True)

            # requeue any jobs whose next_run_at has passed
            requests.post(f"{API}/jobs/requeue-ready", timeout=5)

        except Exception as e:
            print("Worker error:", e, flush=True)

        time.sleep(1)

if __name__ == "__main__":
    main()