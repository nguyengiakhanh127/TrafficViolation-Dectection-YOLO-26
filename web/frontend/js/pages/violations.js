import { $, api, toast, fmtDate, statusBadge, violationLabel } from '../api.js';

let currentPage = 1;
const PAGE_SIZE = 20;
let currentReviewMode = false;

export async function renderViolationsPage(reviewMode = false) {
  currentReviewMode = reviewMode;
  const area = $('content-area');
  area.innerHTML = `
    <div class="table-card">
      <div class="table-toolbar">
        <input id="f-bienso" class="filter-input" placeholder="Biển số..." />
        <select id="f-maloi" class="filter-select">
          <option value="">Tất cả vi phạm</option>
          <option value="DI_SAI_LAN">Đi sai làn</option>
          <option value="DI_NGUOC_CHIEU">Đi ngược chiều</option>
          <option value="DE_VACH_PHAN_LAN">Đè vạch phân làn</option>
          <option value="VUOT_DEN_DO">Vượt đèn đỏ</option>
        </select>
        <select id="f-loaixe" class="filter-select">
          <option value="">Tất cả phương tiện</option>
          <option value="CAR">Ô tô</option>
          <option value="MOTORCYCLE">Xe máy</option>
          <option value="TRUCK">Xe tải</option>
          <option value="BUS">Xe buýt</option>
        </select>
        <select id="f-trangthai" class="filter-select">
          <option value="">Tất cả trạng thái</option>
          <option value="0">Chờ duyệt</option>
          <option value="1">Đã duyệt</option>
          <option value="-1">Từ chối</option>
        </select>
        <button id="f-btn" class="btn-primary" style="padding:7px 16px;font-size:12px">Tìm kiếm</button>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Thời gian</th>
              <th>Camera</th>
              <th>Loại vi phạm</th>
              <th>Phương tiện</th>
              <th>Biển số</th>
              <th>Trạng thái</th>
              <th>Thao tác</th>
              <th>Bằng chứng</th>
            </tr>
          </thead>
          <tbody id="v-tbody">
            <tr><td colspan="8" style="text-align:center;padding:32px">
              <div class="spinner" style="margin:auto"></div>
            </td></tr>
          </tbody>
        </table>
      </div>
      <div class="table-pagination">
        <span class="pagination-info" id="v-page-info">—</span>
        <div class="pagination-btns">
          <button class="btn-page" id="v-prev">Trang trước</button>
          <button class="btn-page" id="v-next">Trang sau</button>
        </div>
      </div>
    </div>`;

  const load = () => loadViolations(reviewMode);
  $('f-btn').addEventListener('click', () => { currentPage = 1; load(); });
  $('v-prev').addEventListener('click', () => { currentPage--; load(); });
  $('v-next').addEventListener('click', () => { currentPage++; load(); });
  load();
}

export async function loadViolations(reviewMode) {
  const params = new URLSearchParams({
    limit: PAGE_SIZE,
    offset: (currentPage - 1) * PAGE_SIZE,
  });
  const bienso = $('f-bienso')?.value.trim();
  const maloi = $('f-maloi')?.value;
  const loaixe = $('f-loaixe')?.value;
  const ts = $('f-trangthai')?.value;
  if (bienso) params.set('bien_so', bienso);
  if (maloi) params.set('ma_loi', maloi);
  if (loaixe) params.set('loai_xe', loaixe);
  if (ts !== '') params.set('trang_thai', ts);

  const tbody = $('v-tbody');
  const cols = 8;
  tbody.innerHTML = `<tr><td colspan="${cols}" style="text-align:center;padding:32px"><div class="spinner" style="margin:auto"></div></td></tr>`;

  try {
    const res = await api(`/api/violations?${params}`);
    const { data, total } = res;
    const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

    $('v-page-info').textContent = `Trang ${currentPage} / ${totalPages}  —  Tổng: ${total} bản ghi`;
    $('v-prev').disabled = currentPage <= 1;
    $('v-next').disabled = currentPage >= totalPages;

    if (!data.length) {
      tbody.innerHTML = `<tr><td colspan="${cols}">
        <div class="empty-state">
          <div class="empty-icon">[ TRỐNG ]</div>
          <p class="empty-text">Không có dữ liệu phù hợp</p>
        </div>
      </td></tr>`;
      return;
    }

    tbody.innerHTML = data.map(row => {
      const evidence = row.duong_dan_bang_chung;
      const evidenceCell = evidence
        ? `<button onclick="App.showEvidence('${row.id}')" class="btn-sm evidence-btn">Xem</button>`
        : `<span class="text-muted">—</span>`;

      const approveRejectBtns = row.trang_thai_duyet === 0
        ? `<button class="btn-sm approve" onclick="App.changeStatus('${row.id}', 1)">Duyệt</button>
           <button class="btn-sm reject"  onclick="App.changeStatus('${row.id}', -1)">Từ chối</button>`
        : '';
      const deleteBtn = `<button class="btn-sm reject" onclick="App.deleteViolation('${row.id}')">Xóa</button>`;

      const actions = `<td>
        <div class="flex gap-2">
          ${approveRejectBtns}
          ${deleteBtn}
        </div>
      </td>`;

      return `<tr>
        <td class="muted font-mono">${fmtDate(row.thoi_gian_vi_pham)}</td>
        <td class="truncate" style="max-width:130px">${row.ten_camera || '—'}</td>
        <td>${violationLabel(row.ma_loi_vi_pham)}</td>
        <td class="muted">${row.loai_phuong_tien || '—'}</td>
        <td class="font-mono">${row.bien_so_xe || '—'}</td>
        <td>${statusBadge(row.trang_thai_duyet)}</td>
        ${actions}
        <td>${evidenceCell}</td>
      </tr>`;
    }).join('');

  } catch (err) {
    toast('Lỗi tải danh sách: ' + err.message, 'error');
  }
}

export async function changeStatus(id, status) {
  try {
    await api(`/api/violations/${id}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ trang_thai: status })
    });
    toast(status === 1 ? 'Đã duyệt vi phạm' : 'Đã từ chối vi phạm', 'success');
    loadViolations(currentReviewMode);
  } catch (err) {
    toast('Lỗi cập nhật: ' + err.message, 'error');
  }
}

export async function deleteViolation(id) {
  if (!confirm('Bạn có chắc chắn muốn xóa bản ghi vi phạm này?')) return;
  try {
    const res = await api(`/api/violations/${id}`, {
      method: 'DELETE'
    });
    if (res && res.success) {
      toast('Đã xóa bản ghi vi phạm thành công', 'success');
      loadViolations(currentReviewMode);
    } else {
      toast('Xóa thất bại: không tìm thấy bản ghi', 'error');
    }
  } catch (err) {
    toast('Lỗi xóa: ' + err.message, 'error');
    console.error('[deleteViolation] ID:', id, 'Error:', err);
  }
}

export async function showEvidence(recordId) {
  const modal = $('evidence-modal');
  const body = $('modal-body');

  modal.classList.remove('hidden');
  body.innerHTML = '<div class="spinner" style="margin:40px auto"></div>';

  try {
    const res = await api(`/api/violations/${recordId}/evidence`);
    if (!res || !res.files || res.files.length === 0) {
      body.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">[ TRỐNG ]</div>
          <p class="empty-text">Không tìm thấy hình ảnh vi phạm.</p>
        </div>`;
      return;
    }

    const images = res.files.filter(f => f.type === 'image');
    const others = res.files.filter(f => f.type !== 'image' && f.type !== 'video');

    if (images.length === 0 && others.length === 0) {
      body.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">[ TRỐNG ]</div>
          <p class="empty-text">Không tìm thấy hình ảnh vi phạm.</p>
        </div>`;
      return;
    }

    let html = '<div class="evidence-gallery">';

    if (images.length > 0) {
      html += '<div class="evidence-section"><h4>Hình ảnh bằng chứng</h4><div class="image-grid">';
      images.forEach(img => {
        html += `
          <div class="evidence-item image-item">
            <a href="${img.url}" target="_blank" title="Click để phóng to">
              <img src="${img.url}" alt="${img.name}" class="evidence-media" />
            </a>
            <div class="evidence-name">${img.name}</div>
          </div>`;
      });
      html += '</div></div>';
    }

    if (others.length > 0) {
      html += '<div class="evidence-section"><h4>Tệp tin khác</h4>';
      others.forEach(oth => {
        html += `
          <div class="evidence-item other-item">
            <a href="${oth.url}" target="_blank" class="btn-primary" style="display:inline-block; margin-top:5px;">
              Tải xuống: ${oth.name}
            </a>
          </div>`;
      });
      html += '</div>';
    }

    html += '</div>';
    body.innerHTML = html;
  } catch (err) {
    body.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">[ LỖI ]</div>
        <p class="empty-text" style="color:var(--red)">Lỗi khi tải bằng chứng: ${err.message}</p>
      </div>`;
  }
}

export function closeEvidenceModal(e) {
  if (e && e.target.id === 'evidence-modal') {
    $('evidence-modal').classList.add('hidden');
  }
}
