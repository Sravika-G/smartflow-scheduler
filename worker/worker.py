import time
import requests

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

            # complete
            r = requests.post(f"{API}/jobs/{job_id}/complete", timeout=5)
            if r.status_code == 200:
                print(f"Completed job {job_id}", flush=True)
            else:
                print(f"Could not complete job {job_id}: {r.text}", flush=True)

        except Exception as e:
            print("Worker error:", e, flush=True)

        time.sleep(1)

if __name__ == "__main__":
    main()