async function searchJobs() {
  const query = document.getElementById("query").value;

  try {
    const results = await request(`/search?query=${query}`);

    const container = document.getElementById("results");
    container.innerHTML = "";

    results.forEach(job => {
      const card = document.createElement("div");
      card.className = "card";

      card.innerHTML = `
        <h3>${job.title}</h3>
        <div class="company">${job.company}</div>

        <div class="tags">
          <div class="tag">External</div>
        </div>

        <br/>
        <button class="btn" onclick="saveExternalJob('${job.id}')">
          Save Job
        </button>
      `;

      container.appendChild(card);
    });

  } catch (err) {
    alert(err.message);
  }
}

async function saveExternalJob(jobId) {
  try {
    await request("/saved-jobs/external", {
      method: "POST",
      body: JSON.stringify({ job_id: jobId }),
    });

    alert("External job saved!");
  } catch (err) {
    alert(err.message);
  }
}