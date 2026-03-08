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

  const total = jobs.length
  const queued = jobs.filter(j => j.status === "queued").length
  const running = jobs.filter(j => j.status === "running").length
  const completed = jobs.filter(j => j.status === "completed").length
  const dead = jobs.filter(j => j.status === "dead").length

  return (
    <div className="page">
  
      <div className="container">
  
        <h1 className="title">SmartFlow Scheduler Dashboard</h1>
  
        <h2 className="section">Jobs</h2>

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
              </tr>
            ))}
          </tbody>
        </table>
  
      </div>
  
    </div>
  )
}

export default App;