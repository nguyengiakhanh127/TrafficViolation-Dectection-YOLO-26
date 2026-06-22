import { $, api, toast, getSession } from '../api.js';

export async function renderCameras() {
  const area = $('content-area');
  const { userRole } = getSession();
  const isAdmin = userRole === 'admin';
  area.innerHTML = `
    ${isAdmin ? `
    <div class="add-camera-form">
      <h3>Thêm Camera mới</h3>
      <div class="form-row">
        <div class="form-group">
          <label class="form-label">Tên camera</label>
          <input id="cam-name" class="form-input" placeholder="VD: CAM_01_NGU_TU_A" />
        </div>
        <div class="form-group">
          <label class="form-label">Tuyến vào</label>
          <input id="cam-in" class="form-input" placeholder="VD: Nguyễn Trãi" />
        </div>
        <div class="form-group">
          <label class="form-label">Tuyến ra</label>
          <input id="cam-out" class="form-input" placeholder="VD: Khuất Duy Tiến" />
        </div>
      </div>
      <button class="btn-primary" id="add-cam-btn" style="margin-top:12px;padding:8px 18px">Thêm Camera</button>
    </div>` : ''}
    <div class="section-header">
      <h2 class="section-title">Danh sách Camera</h2>
    </div>
    <div class="camera-grid" id="camera-grid">
      ${[1, 2, 3].map(() => `<div class="camera-card"><div class="skeleton" style="height:100px;width:100%"></div></div>`).join('')}
    </div>`;

  if (isAdmin) $('add-cam-btn').addEventListener('click', addCamera);
  loadCameras();
}

export async function loadCameras() {
  try {
    const cameras = await api('/api/cameras');
    const grid = $('camera-grid');
    if (!cameras.length) {
      grid.innerHTML = `<div class="empty-state" style="grid-column:1/-1"><div class="empty-icon">[ TRỐNG ]</div><p class="empty-text">Chưa có camera nào</p></div>`;
      return;
    }
    grid.innerHTML = cameras.map(c => `
      <div class="camera-card">
        <div class="camera-status-line">
          <div class="camera-dot"></div>
          <span class="camera-status-text">Online</span>
        </div>
        <div class="camera-name">${c.ten_camera}</div>
        <div class="camera-route">
          ${c.tuyen_duong_vao || '—'} <span>&#x2192;</span> ${c.tuyen_duong_ra || '—'}
        </div>
        <div class="camera-id">ID: ${c.id}</div>
      </div>`).join('');
  } catch (err) { toast('Lỗi tải camera: ' + err.message, 'error'); }
}

export async function addCamera() {
  const name = $('cam-name').value.trim();
  if (!name) { toast('Vui lòng nhập tên camera', 'error'); return; }
  try {
    await api('/api/cameras', {
      method: 'POST',
      body: JSON.stringify({
        ten_camera: name,
        tuyen_vao: $('cam-in').value,
        tuyen_ra: $('cam-out').value
      })
    });
    toast('Đã thêm camera thành công', 'success');
    $('cam-name').value = ''; $('cam-in').value = ''; $('cam-out').value = '';
    loadCameras();
  } catch (err) { toast('Lỗi: ' + err.message, 'error'); }
}
