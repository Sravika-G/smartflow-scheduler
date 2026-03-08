import { useEffect, useState } from "react";

function App() {
  const [jobs, setJobs] = useState([]);

  const fetchJobs = async () => {
    try {
      const res = await fetch("http://127.0.0.1:8000/jobs");
      const data = await res.json();
      setJobs(data);
    } catch (err) {
      console.error("Failed to fetch jobs:", err);
    }
  };

  useEffect(() => {
    fetchJobs();

    const interval = setInterval(fetchJobs, 3000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div style={{ padding: "30px", fontFamily: "Arial" }}>
      <h1>SmartFlow Scheduler Dashboard</h1>

      <h2>Jobs</h2>

      <table border="1" cellPadding="8" style={{ borderCollapse: "collapse", width: "100%" }}>
        <thead>
          <tr>
            <th>ID</th>
            <th>Type</th>
            <th>Status</th>
            <th>Priority</th>
            <th>Attempts</th>
            <th>Predicted Runtime (ms)</th>
            <th>Actual Runtime (ms)</th>
          </tr>
        </thead>

        <tbody>
          {jobs.map((job) => (
            <tr key={job.id}>
              <td>{job.id}</td>
              <td>{job.type}</td>
              <td>{job.status}</td>
              <td>{job.priority}</td>
              <td>{job.attempts}</td>
              <td>{job.predicted_runtime_ms ?? "-"}</td>
              <td>{job.runtime_ms ?? "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default App;