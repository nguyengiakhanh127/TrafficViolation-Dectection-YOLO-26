export const API = '';

export const NAV = {
  admin: [
    { id: 'dashboard', marker: '❖', label: 'Tổng quan' },
    { id: 'cameras', marker: '◉', label: 'Quản lý Camera' },
    { id: 'violations', marker: '☰', label: 'Tất cả Vi phạm' },
    { id: 'review', marker: '✓', label: 'Duyệt Vi phạm' }
  ],
  reviewer: [
    { id: 'review', marker: '✓', label: 'Duyệt Vi phạm' },
    { id: 'violations', marker: '☰', label: 'Tra cứu' }
  ]
};

export const PAGE_TITLES = {
  dashboard: 'Tổng quan Hệ thống',
  cameras: 'Danh sách Camera',
  violations: 'Tất cả Vi phạm',
  review: 'Kiểm duyệt Vi phạm'
};

export function getSession() {
  return {
    token: localStorage.getItem('token'),
    userRole: localStorage.getItem('userRole'),
    userName: localStorage.getItem('userName')
  };
}

export function setSession(token, role, name) {
  localStorage.setItem('token', token);
  localStorage.setItem('userRole', role);
  localStorage.setItem('userName', name);
}

export function clearSession() {
  localStorage.removeItem('token');
  localStorage.removeItem('userRole');
  localStorage.removeItem('userName');
}

export function $ (id) {
  return document.getElementById(id);
}

export function api(path, opts = {}) {
  const { token } = getSession();
  return fetch(API + path, {
    headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json', ...opts.headers },
    ...opts,
  }).then(async r => {
    if (r.status === 401) { logout(); return; }
    if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error(e.detail || r.statusText); }
    return r.json();
  });
}

export function toast(msg, type = 'info') {
  let c = $('toast-container');
  if (!c) { c = document.createElement('div'); c.id = 'toast-container'; document.body.appendChild(c); }
  const t = document.createElement('div');
  t.className = `toast ${type}`;
  const prefix = type === 'success' ? '[OK]' : type === 'error' ? '[ERR]' : '[INFO]';
  t.innerHTML = `<span>${prefix}</span><span>${msg}</span>`;
  c.appendChild(t);
  setTimeout(() => t.remove(), 3500);
}

export function fmtDate(s) {
  if (!s) return '—';
  const d = new Date(s);
  if (isNaN(d)) return s;
  return d.toLocaleString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
}

export function statusBadge(s) {
  if (s === 1) return '<span class="badge approved">Đã duyệt</span>';
  if (s === -1) return '<span class="badge rejected">Từ chối</span>';
  return '<span class="badge pending">Chờ duyệt</span>';
}

export function violationLabel(code) {
  const map = {
    DI_SAI_LAN: 'Đi sai làn',
    DI_NGUOC_CHIEU: 'Đi ngược chiều',
    DE_VACH_PHAN_LAN: 'Đè vạch phân làn',
    VUOT_DEN_DO: 'Vượt đèn đỏ',
    WRONG_LANE: 'Sai làn',
    WRONG_WAY: 'Ngược chiều',
    LINE_CROSSING: 'Vượt vạch',
  };
  return map[code] || code;
}

export function logout() {
  clearSession();
  $('app').classList.add('hidden');
  $('login-screen').classList.remove('hidden');
}
