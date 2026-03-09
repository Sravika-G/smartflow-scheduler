import { useEffect, useState } from "react";

function App() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [jobType, setJobType] = useState("");
  const [payload, setPayload] = useState("{}");
  const [priority, setPriority] = useState(5);
  const [maxAttempts, setMaxAttempts] = useState(3);

  const fetchJobs = async () => {
    try {
      setLoading(true);
      setError("");

      const res = await fetch("http://127.0.0.1:8000/jobs");

      if (!res.ok) {
        throw new Error(`Backend returned ${res.status}`);
      }

      const data = await res.json();

      if (!Array.isArray(data)) {
        throw new Error("Expected jobs API to return an array");
      }

      setJobs(data);
    } catch (err) {
      console.error("Failed to fetch jobs:", err);
      setError(err.message || "Failed to load jobs");
    } finally {
      setLoading(false);
    }
  };

  const createJob = async (e) => {
    e.preventDefault();

    try {
      setError("");

      await fetch("http://127.0.0.1:8000/jobs", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          type: jobType,
          payload: JSON.parse(payload),
          priority: Number(priority),
          max_attempts: Number(maxAttempts),
        }),
      });

      setJobType("");
      setPayload("{}");
      setPriority(5);
      setMaxAttempts(3);

      fetchJobs();
    } catch (err) {
      console.error("Failed to create job:", err);
      setError(err.message || "Failed to create job");
    }
  };

  useEffect(() => {
    fetchJobs();

    const interval = setInterval(fetchJobs, 3000);
    return () => clearInterval(interval);
  }, []);

  const total = jobs.length;
  const queued = jobs.filter((j) => j.status === "queued").length;
  const running = jobs.filter((j) => j.status === "running").length;
  const completed = jobs.filter((j) => j.status === "completed").length;
  const dead = jobs.filter((j) => j.status === "dead").length;

  return (
    <div className="page">
      <div className="container">
        <h1 className="title">SmartFlow Scheduler Dashboard</h1>

        <div className="metrics">
          <div className="card">
            <h3>Total Jobs</h3>
            <p>{total}</p>
          </div>

          <div className="card">
            <h3>Queued</h3>
            <p>{queued}</p>
          </div>

          <div className="card">
            <h3>Running</h3>
            <p>{running}</p>
          </div>

          <div className="card">
            <h3>Completed</h3>
            <p>{completed}</p>
          </div>

          <div className="card">
            <h3>Dead</h3>
            <p>{dead}</p>
          </div>
        </div>

        <h2 className="section">Create Job</h2>

        <form onSubmit={createJob} style={{ marginBottom: "30px" }}>
          <div style={{ display: "grid", gap: "12px" }}>
            <input
              type="text"
              placeholder="Job Type"
              value={jobType}
              onChange={(e) => setJobType(e.target.value)}
              style={{ padding: "10px" }}
              required
            />

            <textarea
              placeholder='Payload JSON, for example: {"message":"hello"}'
              value={payload}
              onChange={(e) => setPayload(e.target.value)}
              rows={4}
              style={{ padding: "10px" }}
            />

            <input
              type="number"
              placeholder="Priority"
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
              style={{ padding: "10px" }}
              min="1"
              max="10"
            />

            <input
              type="number"
              placeholder="Max Attempts"
              value={maxAttempts}
              onChange={(e) => setMaxAttempts(e.target.value)}
              style={{ padding: "10px" }}
              min="1"
              max="10"
            />

            <button type="submit" style={{ padding: "12px", cursor: "pointer" }}>
              Create Job
            </button>
          </div>
        </form>

        <h2 className="section">Jobs</h2>

        {loading && <p>Loading jobs...</p>}

        {error && <p style={{ color: "red", fontWeight: "bold" }}>Failed: {error}</p>}

        {!loading && !error && (
          <table className="jobs-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Type</th>
                <th>Status</th>
                <th>Priority</th>
                <th>Attempts</th>
                <th>Predicted Runtime (ms)</th>
                <th>Actual Runtime (ms)</th>
                <th>Prediction Error (ms)</th>
              </tr>
            </thead>

            <tbody>
              {jobs.map((job) => (
                <tr key={job.id}>
                  <td>{job.id}</td>
                  <td>{job.type}</td>
                  <td className={`status ${job.status}`}>{job.status}</td>
                  <td>{job.priority}</td>
                  <td>{job.attempts}</td>
                  <td>{job.predicted_runtime_ms ?? "-"}</td>
                  <td>{job.runtime_ms ?? "-"}</td>
                  <td>
                    {job.predicted_runtime_ms != null && job.runtime_ms != null
                      ? Math.abs(job.predicted_runtime_ms - job.runtime_ms)
                      : "-"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

export default App;