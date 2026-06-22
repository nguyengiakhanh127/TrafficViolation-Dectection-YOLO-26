import { $, setSession, logout } from './api.js';
import { enterApp } from './router.js';
import { API } from './api.js';

export async function doLogin(e) {
  e.preventDefault();
  const u = $('login-username').value.trim();
  const p = $('login-password').value;
  const btn = $('login-btn');
  const errEl = $('login-error');
  errEl.classList.add('hidden');
  $('login-btn-text').textContent = 'Đang đăng nhập...';
  $('login-spinner').classList.remove('hidden');
  btn.disabled = true;

  try {
    const form = new URLSearchParams();
    form.append('username', u);
    form.append('password', p);
    const res = await fetch(`${API}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: form,
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Đăng nhập thất bại');

    setSession(data.access_token, data.role, data.full_name);
    enterApp();
  } catch (err) {
    errEl.textContent = err.message;
    errEl.classList.remove('hidden');
  } finally {
    $('login-btn-text').textContent = 'Đăng nhập';
    $('login-spinner').classList.add('hidden');
    btn.disabled = false;
  }
}
