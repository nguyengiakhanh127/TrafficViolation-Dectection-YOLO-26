import { $, api, toast, violationLabel } from '../api.js';

let chartDay = null, chartType = null, chartVehicle = null;

export async function renderDashboard() {
  const area = $('content-area');
  area.innerHTML = `
    <div class="stats-grid" id="stats-grid">
      ${[1, 2, 3, 4].map(() => `<div class="stat-card"><div class="skeleton" style="width:100%;height:70px;"></div></div>`).join('')}
    </div>
    <div class="charts-grid">
      <div class="chart-card full">
        <div class="chart-header">
          <span class="chart-title">Vi phạm theo ngày</span>
          <span class="chart-sub">7 ngày gần nhất</span>
        </div>
        <div class="chart-wrap"><canvas id="chart-day"></canvas></div>
      </div>
      <div class="chart-card">
        <div class="chart-header"><span class="chart-title">Phân loại vi phạm</span></div>
        <div class="chart-wrap"><canvas id="chart-type"></canvas></div>
      </div>
      <div class="chart-card">
        <div class="chart-header"><span class="chart-title">Phương tiện vi phạm</span></div>
        <div class="chart-wrap"><canvas id="chart-vehicle"></canvas></div>
      </div>
    </div>`;

  try {
    const [overview, byDay, byType, byVehicle] = await Promise.all([
      api('/api/stats/overview'),
      api('/api/stats/by-day?days=7'),
      api('/api/stats/by-type'),
      api('/api/stats/by-vehicle'),
    ]);

    $('stats-grid').innerHTML = `
      <div class="stat-card">
        <div class="stat-label">Tổng vi phạm</div>
        <div class="stat-value">${overview.total_violations}</div>
        <div class="stat-sub">Tất cả bản ghi</div>
      </div>
      <div class="stat-card pending">
        <div class="stat-label">Chờ duyệt</div>
        <div class="stat-value">${overview.pending}</div>
        <div class="stat-sub">Cần xử lý</div>
      </div>
      <div class="stat-card approved">
        <div class="stat-label">Đã duyệt</div>
        <div class="stat-value">${overview.approved}</div>
        <div class="stat-sub">Đã xử lý</div>
      </div>
      <div class="stat-card cameras">
        <div class="stat-label">Camera</div>
        <div class="stat-value">${overview.total_cameras}</div>
        <div class="stat-sub">Đang hoạt động</div>
      </div>`;

    /* Chart defaults — classic muted style */
    Chart.defaults.color = '#555e7a';
    Chart.defaults.font = { family: 'Inter', size: 11 };

    if (chartDay) chartDay.destroy();
    chartDay = new Chart($('chart-day'), {
      type: 'bar',
      data: {
        labels: byDay.labels,
        datasets: [{
          label: 'Vi phạm',
          data: byDay.counts,
          backgroundColor: 'rgba(74,124,247,0.55)',
          borderColor: '#4a7cf7',
          borderWidth: 1,
          borderRadius: 2,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { color: 'rgba(44,49,72,0.8)' }, border: { color: '#2c3148' } },
          y: { beginAtZero: true, grid: { color: 'rgba(44,49,72,0.8)' }, border: { color: '#2c3148' }, ticks: { stepSize: 1 } }
        }
      }
    });

    const PIE_COLORS = ['#4a7cf7', '#d4a017', '#3dba6f', '#d94f4f', '#7aa3ff', '#8b92aa', '#555e7a', '#2c3148'];

    if (chartType) chartType.destroy();
    chartType = new Chart($('chart-type'), {
      type: 'doughnut',
      data: {
        labels: byType.labels.map(violationLabel),
        datasets: [{
          data: byType.counts,
          backgroundColor: PIE_COLORS,
          borderWidth: 1,
          borderColor: '#1e2230',
          hoverOffset: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: 'bottom', labels: { padding: 10, boxWidth: 10, font: { size: 11 } } } }
      }
    });

    if (chartVehicle) chartVehicle.destroy();
    chartVehicle = new Chart($('chart-vehicle'), {
      type: 'doughnut',
      data: {
        labels: byVehicle.labels,
        datasets: [{
          data: byVehicle.counts,
          backgroundColor: PIE_COLORS,
          borderWidth: 1,
          borderColor: '#1e2230',
          hoverOffset: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: 'bottom', labels: { padding: 10, boxWidth: 10, font: { size: 11 } } } }
      }
    });

  } catch (err) {
    toast('Lỗi tải dashboard: ' + err.message, 'error');
  }
}
