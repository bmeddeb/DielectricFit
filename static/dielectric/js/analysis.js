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
  if (kk) new Chart(kk.getContext('2d'), { type: 'line', data: { labels: frequencies, datasets: [{ data: frequencies.map(f => Math.random() * 0.1), borderColor: 'rgb(99, 102, 241)', backgroundColor: 'rgba(99, 102, 241, 0.1)', pointRadius: 2 }] }, options: analysisChartOptions });
});
