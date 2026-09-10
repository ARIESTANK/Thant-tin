let charts = {};

const $ = (id) => document.getElementById(id);
const fmt = (n) => new Intl.NumberFormat().format(n);

function destroyCharts() {
  Object.values(charts).forEach(c => c && c.destroy());
  charts = {};
}

function baseOptions() {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { labels: { boxWidth: 10, usePointStyle: true } }
    },
    scales: {
      x: { grid: { display: false }, ticks: { color: "#718096" } },
      y: { grid: { color: "#eef1f5" }, ticks: { color: "#718096" } }
    }
  };
}

function render(data) {
  destroyCharts();

  $("students").textContent = fmt(data.overview.students);
  $("enrollmentRate").textContent = data.overview.enrollment_rate + "%";
  $("enrolled").textContent = fmt(data.overview.enrolled);
  $("missing").textContent = fmt(data.overview.missing_cells);
  $("bestClassifier").textContent = "Best: " + data.best_classifier;
  $("bestRegressor").textContent = "Best: " + data.best_regressor;

  charts.enrollment = new Chart($("enrollmentChart"), {
    type: "doughnut",
    data: {
      labels: data.enrollment.map(x => x.status),
      datasets: [{ data: data.enrollment.map(x => x.count), borderWidth: 0 }]
    },
    options: { responsive: true, maintainAspectRatio: false, cutout: "66%", plugins: { legend: { position: "bottom" } } }
  });

  charts.score = new Chart($("scoreChart"), {
    type: "bar",
    data: { labels: data.score_hist.map(x => x.label), datasets: [{ label: "Students", data: data.score_hist.map(x => x.count), borderRadius: 5 }] },
    options: baseOptions()
  });

  charts.classification = new Chart($("classificationChart"), {
    type: "bar",
    data: {
      labels: data.classification.map(x => x.model),
      datasets: [
        { label: "Accuracy", data: data.classification.map(x => x.accuracy) },
        { label: "Weighted F1", data: data.classification.map(x => x.f1) }
      ]
    },
    options: { ...baseOptions(), scales: { ...baseOptions().scales, y: { min: 0, max: 1, grid: { color: "#eef1f5" } } } }
  });

  charts.regression = new Chart($("regressionChart"), {
    type: "bar",
    data: {
      labels: data.regression.map(x => x.model),
      datasets: [
        { label: "R²", data: data.regression.map(x => x.r2) },
        { label: "RMSE", data: data.regression.map(x => x.rmse) }
      ]
    },
    options: baseOptions()
  });

  charts.importance = new Chart($("importanceChart"), {
    type: "bar",
    data: {
      labels: [...data.feature_importance].reverse().map(x => x.feature),
      datasets: [{ label: "Permutation importance", data: [...data.feature_importance].reverse().map(x => x.importance) }]
    },
    options: { ...baseOptions(), indexAxis: "y" }
  });

  charts.scatter = new Chart($("scatterChart"), {
    type: "scatter",
    data: {
      datasets: [{ label: "Students", data: data.income_score.map(x => ({x: x.income, y: x.score})), pointRadius: 3 }]
    },
    options: {
      ...baseOptions(),
      scales: {
        x: { title: { display: true, text: "Family monthly income (MMK)" }, grid: { display: false } },
        y: { title: { display: true, text: "Matriculation score" }, grid: { color: "#eef1f5" } }
      }
    }
  });

  const statuses = data.enrollment.map(x => x.status);
  charts.region = new Chart($("regionChart"), {
    type: "bar",
    data: {
      labels: data.region_enrollment.map(x => x.region),
      datasets: statuses.map(s => ({ label: s, data: data.region_enrollment.map(x => x[s] || 0) }))
    },
    options: { ...baseOptions(), indexAxis: "y" }
  });

  charts.field = new Chart($("fieldChart"), {
    type: "bar",
    data: {
      labels: data.field_counts.map(x => x.field),
      datasets: [{ label: "Students", data: data.field_counts.map(x => x.count) }]
    },
    options: { ...baseOptions(), indexAxis: "y" }
  });
}

async function loadDashboard() {
  $("refreshBtn").textContent = "Loading…";
  try {
    const res = await fetch("/api/dashboard/");
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Dashboard API error");
    render(data);
  } catch (err) {
    alert(err.message);
  } finally {
    $("refreshBtn").textContent = "↻ Refresh analysis";
  }
}

$("refreshBtn").addEventListener("click", loadDashboard);

$("predictionForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = new FormData(e.target);
  const payload = Object.fromEntries(form.entries());
  const result = $("predictionResult");
  result.classList.remove("hidden");
  result.innerHTML = "Running prediction…";

  try {
    const res = await fetch("/api/predict/", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Prediction failed");

    result.innerHTML = `<div>${data.model_name}</div><strong>${data.prediction}</strong><div>Predicted matriculation score</div>`;
  } catch (err) {
    result.innerHTML = `<b>Error:</b> ${err.message}`;
  }
});

loadDashboard();
