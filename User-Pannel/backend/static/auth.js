(() => {
  const tabs = document.querySelectorAll('[data-auth-tab]');
  const loginPanel = document.getElementById('loginPanel');
  const registerPanel = document.getElementById('registerPanel');
  const heading = document.getElementById('authHeading');
  const subheading = document.getElementById('authSubheading');
  const requestedPath = new URLSearchParams(window.location.search).get('next');
  const safeNextPath = requestedPath?.startsWith('/') && !requestedPath.startsWith('//') ? requestedPath : '/';

  function refreshIcons() {
    if (window.lucide) window.lucide.createIcons({ attrs: { 'aria-hidden': 'true' } });
  }

  function setTab(tab) {
    const loginActive = tab === 'login';
    tabs.forEach((button) => {
      const active = button.dataset.authTab === tab;
      button.classList.toggle('active', active);
      button.setAttribute('aria-selected', String(active));
    });
    loginPanel.classList.toggle('active', loginActive);
    registerPanel.classList.toggle('active', !loginActive);
    loginPanel.hidden = !loginActive;
    registerPanel.hidden = loginActive;
    heading.innerHTML = loginActive ? 'Welcome<br><em>back.</em>' : 'Your wardrobe,<br><em>considered.</em>';
    subheading.textContent = loginActive
      ? 'Return to your private wardrobe, saved pieces and order history.'
      : 'Create your account for private access, personal service and a more considered experience.';
    clearAlert('loginAlert');
    clearAlert('registerAlert');
  }

  function showAlert(id, message, success = false) {
    const alert = document.getElementById(id);
    alert.textContent = message;
    alert.classList.toggle('success', success);
    alert.classList.add('show');
  }

  function clearAlert(id) {
    const alert = document.getElementById(id);
    alert?.classList.remove('show', 'success');
  }

  async function request(url, body) {
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify(body),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || 'Something went wrong. Please try again.');
    return data;
  }

  function setLoading(button, loading, defaultLabel) {
    button.disabled = loading;
    button.textContent = loading ? 'Please wait…' : defaultLabel;
  }

  tabs.forEach((button) => button.addEventListener('click', () => setTab(button.dataset.authTab)));

  document.querySelectorAll('[data-password-toggle]').forEach((button) => {
    button.addEventListener('click', () => {
      const input = document.getElementById(button.dataset.passwordToggle);
      const showing = input.type === 'text';
      input.type = showing ? 'password' : 'text';
      button.setAttribute('aria-label', showing ? 'Show password' : 'Hide password');
      button.innerHTML = `<i data-lucide="${showing ? 'eye' : 'eye-off'}"></i>`;
      refreshIcons();
    });
  });

  const rememberedEmail = localStorage.getItem('styleaccess-login-email');
  if (rememberedEmail) {
    document.getElementById('loginEmail').value = rememberedEmail;
    document.getElementById('rememberEmail').checked = true;
  }

  const registerPassword = document.getElementById('registerPassword');
  const passwordMeter = document.getElementById('passwordMeter');
  const passwordStrength = document.getElementById('passwordStrength');
  registerPassword?.addEventListener('input', () => {
    const value = registerPassword.value;
    let score = 0;
    if (value.length >= 8) score += 1;
    if (/[A-Z]/.test(value) && /[a-z]/.test(value)) score += 1;
    if (/\d/.test(value)) score += 1;
    if (/[^A-Za-z0-9]/.test(value) || value.length >= 12) score += 1;
    passwordMeter.dataset.score = String(score);
    passwordStrength.textContent = !value
      ? 'Use 8 or more characters'
      : ['Too short', 'Keep going', 'Good password', 'Strong password'][Math.max(0, score - 1)];
  });

  document.getElementById('loginForm').addEventListener('submit', async (event) => {
    event.preventDefault();
    clearAlert('loginAlert');
    if (!event.currentTarget.checkValidity()) {
      event.currentTarget.reportValidity();
      return;
    }
    const email = document.getElementById('loginEmail').value.trim().toLowerCase();
    const password = document.getElementById('loginPassword').value;
    const button = document.getElementById('loginButton');
    setLoading(button, true, 'Sign in');
    try {
      const user = await request('/api/login', { email, password });
      if (document.getElementById('rememberEmail').checked) localStorage.setItem('styleaccess-login-email', email);
      else localStorage.removeItem('styleaccess-login-email');
      window.location.replace(user.role === 'admin' ? '/admin' : safeNextPath);
    } catch (error) {
      showAlert('loginAlert', error.message);
      setLoading(button, false, 'Sign in');
    }
  });

  document.getElementById('registerForm').addEventListener('submit', async (event) => {
    event.preventDefault();
    clearAlert('registerAlert');
    if (!event.currentTarget.checkValidity()) {
      event.currentTarget.reportValidity();
      return;
    }
    const name = document.getElementById('registerName').value.trim();
    const email = document.getElementById('registerEmail').value.trim().toLowerCase();
    const password = document.getElementById('registerPassword').value;
    const button = document.getElementById('registerButton');
    setLoading(button, true, 'Create my account');
    try {
      await request('/api/register', { name, email, password });
      document.getElementById('registerForm').reset();
      document.getElementById('loginEmail').value = email;
      setTab('login');
      showAlert('loginAlert', 'Your account is ready. Sign in to continue.', true);
      document.getElementById('loginPassword').focus();
    } catch (error) {
      showAlert('registerAlert', error.message);
    } finally {
      setLoading(button, false, 'Create my account');
    }
  });

  (async () => {
    try {
      const response = await fetch('/api/me', { credentials: 'same-origin' });
      if (!response.ok) return;
      const user = await response.json();
      window.location.replace(user.role === 'admin' ? '/admin' : safeNextPath);
    } catch {
      // The page remains available when there is no active session.
    }
  })();

  refreshIcons();
})();
