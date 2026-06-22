import { $, getSession, NAV, PAGE_TITLES } from './api.js';
import { renderDashboard } from './pages/dashboard.js';
import { renderCameras } from './pages/cameras.js';
import { renderViolationsPage } from './pages/violations.js';

export function startClock() {
  const el = $('topbar-time');
  const tick = () => { if (el) el.textContent = new Date().toLocaleTimeString('vi-VN'); };
  tick(); setInterval(tick, 1000);
}

export function enterApp() {
  const { userRole } = getSession();
  $('login-screen').classList.add('hidden');
  $('app').classList.remove('hidden');
  buildSidebar();
  updateUserCard();
  startClock();
  const defaultPage = userRole === 'admin' ? 'dashboard' : 'review';
  navigate(defaultPage);
}

export function buildSidebar() {
  const { userRole } = getSession();
  const nav = $('sidebar-nav');
  nav.innerHTML = '';

  const label = document.createElement('div');
  label.className = 'nav-section-label';
  label.textContent = 'Điều hướng';
  nav.appendChild(label);

  (NAV[userRole] || NAV.reviewer).forEach(item => {
    const el = document.createElement('div');
    el.className = 'nav-item';
    el.dataset.page = item.id;
    el.innerHTML = `<span class="nav-marker">${item.marker}</span><span class="nav-label">${item.label}</span>`;
    el.addEventListener('click', () => navigate(item.id));
    nav.appendChild(el);
  });
}

export function updateUserCard() {
  const { userRole, userName } = getSession();
  $('user-name').textContent = userName;
  $('user-avatar').textContent = userName.charAt(0).toUpperCase();
  const badge = $('user-role-badge');
  badge.textContent = userRole === 'admin' ? 'ADMIN' : 'REVIEWER';
  badge.className = `user-role-badge ${userRole !== 'admin' ? 'reviewer' : ''}`;
}

export function setActiveNav(pageId) {
  document.querySelectorAll('.nav-item').forEach(el => {
    el.classList.toggle('active', el.dataset.page === pageId);
  });
}

export function navigate(pageId) {
  setActiveNav(pageId);
  $('page-title').textContent = PAGE_TITLES[pageId] || pageId;
  const area = $('content-area');
  area.innerHTML = '';
  
  // Gọi hàm render của trang tương ứng
  if (pageId === 'dashboard') {
    renderDashboard();
  } else if (pageId === 'cameras') {
    renderCameras();
  } else if (pageId === 'violations') {
    renderViolationsPage(false);
  } else if (pageId === 'review') {
    renderViolationsPage(true);
  }
}
