async function loadStats() {
  try {
    const stats = await request("/stats");

    document.getElementById("totalJobs").innerText = stats.total_jobs;
    document.getElementById("savedJobs").innerText = stats.saved_jobs;

  } catch (err) {
    console.error(err);
  }
}

document.addEventListener("DOMContentLoaded", loadStats);