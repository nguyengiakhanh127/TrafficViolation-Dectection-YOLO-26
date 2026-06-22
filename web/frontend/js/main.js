import { $, api, logout } from './api.js';
import { doLogin } from './auth.js';
import { enterApp, navigate } from './router.js';
import { changeStatus, deleteViolation, showEvidence, closeEvidenceModal } from './pages/violations.js';

// Khởi tạo App namespace cho các event handler inline onclick trong HTML
window.App = {
  changeStatus,
  deleteViolation,
  showEvidence,
  closeEvidenceModal,
  navigate
};

function initApp() {
  // Sidebar Toggle
  const sidebarToggle = $('sidebar-toggle');
  if (sidebarToggle) {
    sidebarToggle.addEventListener('click', () => {
      $('sidebar').classList.toggle('collapsed');
    });
  }

  // Logout
  const logoutBtn = $('logout-btn');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', logout);
  }

  // Login form
  const loginForm = $('login-form');
  if (loginForm) {
    loginForm.addEventListener('submit', doLogin);
  }

  // Restore session
  const token = localStorage.getItem('token');
  if (token) {
    api('/api/auth/me').then(me => {
      if (me) {
        enterApp();
      } else {
        logout();
      }
    }).catch(() => logout());
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initApp);
} else {
  initApp();
}
