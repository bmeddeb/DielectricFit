document.addEventListener('DOMContentLoaded', function () {
  const analysisChartOptions = {
    maintainAspectRatio: false,
    responsive: true,
    plugins: { legend: { display: false }, title: { display: false } },
    scales: {
      x: {
        type: 'logarithmic',
        grid: { color: '#e2e8f0' },
        ticks: { color: '#64748b', font: { size: 10 } },
        title: { display: true, text: 'Frequency (Hz)', color: '#64748b', font: { size: 11 } },
      },
      y: { grid: { color: '#e2e8f0' }, ticks: { color: '#64748b', font: { size: 10 } } },
    },
  };

  const frequencies = Array.from({ length: 50 }, (_, i) => Math.pow(10, i / 10 + 2));

  const real = document.getElementById('realPartPlot');
  if (real) new Chart(real.getContext('2d'), { type: 'line', data: { labels: frequencies, datasets: [{ label: "ε'", data: frequencies.map(f => 10 - Math.log10(f)), borderColor: 'rgb(59, 130, 246)', backgroundColor: 'rgba(59, 130, 246, 0.1)', pointRadius: 2 }] }, options: analysisChartOptions });

  const imag = document.getElementById('imagPartPlot');
  if (imag) new Chart(imag.getContext('2d'), { type: 'line', data: { labels: frequencies, datasets: [{ label: "ε''", data: frequencies.map(f => 2 * Math.exp(-Math.pow((Math.log10(f) - 4) / 2, 2))), borderColor: 'rgb(239, 68, 68)', backgroundColor: 'rgba(239, 68, 68, 0.1)', pointRadius: 2 }] }, options: analysisChartOptions });

  const cc = document.getElementById('coleColePlot');
  if (cc) new Chart(cc.getContext('2d'), { type: 'line', data: { labels: frequencies, datasets: [{ data: frequencies.map(f => Math.sin(Math.log10(f))), borderColor: 'rgb(16, 185, 129)', backgroundColor: 'rgba(16, 185, 129, 0.1)', pointRadius: 2 }] }, options: analysisChartOptions });

  const kk = document.getElementById('kkResidualsPlot');
  if (kk) {
    const residuals = frequencies.map(f => 0.02 + 0.02 * Math.sin(Math.log10(f)) + (Math.random() - 0.5) * 0.01);
    const ctx = kk.getContext('2d');
    new Chart(ctx, {
      type: 'line',
      data: { labels: frequencies, datasets: [{ data: residuals, borderColor: 'rgb(99, 102, 241)', backgroundColor: 'rgba(99, 102, 241, 0.1)', pointRadius: 2 }] },
      options: analysisChartOptions
    });

    // Compute KK residual metrics
    const rmse = Math.sqrt(residuals.reduce((acc, r) => acc + r * r, 0) / residuals.length);
    const maxAbs = residuals.reduce((m, r) => Math.max(m, Math.abs(r)), 0);

    const rmseEl = document.getElementById('kkRmse');
    const maxEl = document.getElementById('kkMaxRes');
    const badge = document.getElementById('kkBadge');
    const card = document.getElementById('kkBadgeCard');
    if (rmseEl) rmseEl.textContent = rmse.toFixed(3);
    if (maxEl) maxEl.textContent = maxAbs.toFixed(3);

    // Thresholds (should match settings/documentation defaults)
    const RMSE_THR = 0.02;
    const MAX_THR = 0.1;
    const pass = rmse <= RMSE_THR && maxAbs <= MAX_THR;

    if (badge && card) {
      if (pass) {
        badge.textContent = 'PASS';
        badge.className = 'text-xs px-2 py-0.5 rounded bg-green-600 text-white';
        card.className = 'mb-4 p-3 bg-green-50 border border-green-200 rounded-lg';
      } else {
        badge.textContent = 'FAIL';
        badge.className = 'text-xs px-2 py-0.5 rounded bg-red-600 text-white';
        card.className = 'mb-4 p-3 bg-red-50 border border-red-200 rounded-lg';
      }
    }
  }
});
