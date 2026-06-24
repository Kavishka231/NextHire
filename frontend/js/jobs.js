async function loadJobs() {
  try {
    const jobs = await request("/jobs");

    const container = document.getElementById("jobsContainer");
    container.innerHTML = "";

    jobs.forEach(job => {
      const card = document.createElement("div");
      card.className = "card";

      card.innerHTML = `
        <h3>${job.title}</h3>
        <div class="company">${job.company} • ${job.location || "Remote"}</div>

        <div class="tags">
          <div class="tag">${job.type || "Full-time"}</div>
          <div class="tag">${job.level || "Mid"}</div>
        </div>

        <br/>
        <button class="btn" onclick="saveJob('${job.id}')">
          Save Job
        </button>
      `;

      container.appendChild(card);
    });

  } catch (err) {
    console.error(err);
  }
}

async function saveJob(jobId) {
  try {
    await request("/saved-jobs", {
      method: "POST",
      body: JSON.stringify({ job_id: jobId }),
    });

    alert("Job saved!");
  } catch (err) {
    alert(err.message);
  }
}

document.addEventListener("DOMContentLoaded", loadJobs);