(() => {
  const tabs = document.querySelectorAll('[data-auth-tab]');
  const loginPanel = document.getElementById('loginPanel');
  const registerPanel = document.getElementById('registerPanel');
  const heading = document.getElementById('authHeading');
  const subheading = document.getElementById('authSubheading');

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
    heading.textContent = loginActive ? 'Welcome back.' : 'Join StyleAccess.';
    subheading.textContent = loginActive
      ? 'Sign in to see your bag, saved pieces and order history.'
      : 'Create an account for a more considered shopping experience.';
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
      window.location.replace(user.role === 'admin' ? '/admin' : '/');
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
      window.location.replace(user.role === 'admin' ? '/admin' : '/');
    } catch {
      // The page remains available when there is no active session.
    }
  })();

  refreshIcons();
})();
