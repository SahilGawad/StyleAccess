(() => {
  let products = [];
  let dashboard = { orders: [] };
  let toastTimer;
  const fallbackImage = '/static/images/regent-blazer.jpg';
  const modal = document.getElementById('productModal');
  const overlay = document.getElementById('adminOverlay');

  const money = (value) => new Intl.NumberFormat('en-IN', {
    style: 'currency', currency: 'INR', maximumFractionDigits: 0,
  }).format(Number(value) || 0);

  const escapeHtml = (value = '') => String(value).replace(/[&<>'"]/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;',
  }[char]));

  function refreshIcons() {
    if (window.lucide) window.lucide.createIcons({ attrs: { 'aria-hidden': 'true' } });
  }

  function showToast(message, icon = 'check-circle') {
    const toast = document.getElementById('toast');
    const text = document.getElementById('toastText');
    toast.querySelector('svg')?.remove();
    const iconNode = document.createElement('i');
    iconNode.setAttribute('data-lucide', icon);
    toast.prepend(iconNode);
    text.textContent = message;
    toast.classList.add('show');
    refreshIcons();
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove('show'), 2800);
  }

  function showFormError(message) {
    const alert = document.getElementById('productFormAlert');
    alert.textContent = message;
    alert.classList.add('show');
  }

  async function requestJson(url, options = {}) {
    const response = await fetch(url, { credentials: 'same-origin', ...options });
    if (response.status === 401 || response.status === 403) {
      window.location.replace('/login');
      throw new Error('Your session has ended.');
    }
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || 'Something went wrong. Please try again.');
    return data;
  }

  function stockClass(stock) {
    if (Number(stock) <= 0) return 'out';
    if (Number(stock) <= 8) return 'low';
    return '';
  }

  function stockLabel(stock) {
    if (Number(stock) <= 0) return 'Out of stock';
    if (Number(stock) <= 8) return `${stock} · Low`;
    return `${stock} in stock`;
  }

  function renderInventory() {
    const rows = document.getElementById('inventoryRows');
    const query = document.getElementById('inventorySearch').value.trim().toLowerCase();
    const visible = products.filter((product) => {
      return !query || product.name.toLowerCase().includes(query) || String(product.category).toLowerCase().includes(query);
    });
    if (!visible.length) {
      rows.innerHTML = `<tr><td colspan="6"><div class="empty-state"><i data-lucide="${products.length ? 'search-x' : 'shirt'}"></i><p>${products.length ? 'No products match your search.' : 'Your published inventory is empty.'}</p><button class="btn btn-outline" type="button" id="emptyAddProduct">Add your first product</button></div></td></tr>`;
      refreshIcons();
      return;
    }
    rows.innerHTML = visible.map((product) => {
      const id = encodeURIComponent(product._id);
      const sizes = Array.isArray(product.sizes) ? product.sizes.join(', ') : product.sizes;
      return `<tr>
        <td><div class="inventory-product"><img src="${escapeHtml(product.imageUrl || fallbackImage)}" alt="" onerror="this.onerror=null;this.src='${fallbackImage}'"><div><strong>${escapeHtml(product.name)}</strong><span>${escapeHtml(product.badge || 'Core collection')}</span></div></div></td>
        <td>${escapeHtml(product.category || 'Essentials')}</td>
        <td><strong>${money(product.price)}</strong>${Number(product.compareAt) > Number(product.price) ? `<br><s style="color:#8f948f">${money(product.compareAt)}</s>` : ''}</td>
        <td><span class="stock-pill ${stockClass(product.stock)}">${stockLabel(product.stock)}</span></td>
        <td>${escapeHtml(sizes || '—')}</td>
        <td><div class="table-actions"><button type="button" data-edit-product="${id}" aria-label="Edit ${escapeHtml(product.name)}"><i data-lucide="pencil"></i></button><button class="delete" type="button" data-delete-product="${id}" aria-label="Delete ${escapeHtml(product.name)}"><i data-lucide="trash-2"></i></button></div></td>
      </tr>`;
    }).join('');
    refreshIcons();
  }

  function renderDashboard() {
    document.getElementById('productCount').textContent = dashboard.productCount ?? products.length;
    document.getElementById('stockCount').textContent = dashboard.stockCount ?? 0;
    document.getElementById('orderCount').textContent = dashboard.orderCount ?? 0;
    document.getElementById('catalogValue').textContent = money(dashboard.catalogValue ?? 0);
    const rows = document.getElementById('orderRows');
    if (!dashboard.orders?.length) {
      rows.innerHTML = '<tr><td colspan="6"><div class="empty-state"><i data-lucide="package-open"></i><p>No customer orders have been placed yet.</p></div></td></tr>';
      refreshIcons();
      return;
    }
    rows.innerHTML = dashboard.orders.map((order) => {
      const address = order.shipping_address || {};
      const customer = address.full_name || 'Customer';
      const date = order.created_at ? new Date(order.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' }) : 'Recently';
      const items = (order.items || []).map((item) => `${item.name} × ${item.qty}`).join(', ');
      return `<tr>
        <td><strong>#${escapeHtml(String(order._id).slice(-8).toUpperCase())}</strong><br><span style="color:#6f756f;font-size:9px">${date}</span></td>
        <td>${escapeHtml(customer)}<br><span style="color:#6f756f;font-size:9px">${escapeHtml(address.city || '')}</span></td>
        <td class="order-items-cell">${escapeHtml(items)}</td>
        <td><strong>${money(order.total)}</strong></td>
        <td style="text-transform:uppercase;font-size:9px;font-weight:700">${escapeHtml(order.payment_method || '—')}</td>
        <td><span class="status-pill">${escapeHtml(order.status || 'confirmed')}</span></td>
      </tr>`;
    }).join('');
    refreshIcons();
  }

  async function loadData() {
    try {
      const [catalogData, dashboardData] = await Promise.all([
        requestJson('/api/admin/catalog'),
        requestJson('/api/admin/dashboard'),
      ]);
      products = catalogData;
      dashboard = dashboardData;
      renderInventory();
      renderDashboard();
    } catch (error) {
      document.getElementById('inventoryRows').innerHTML = `<tr><td colspan="6"><div class="empty-state"><i data-lucide="circle-alert"></i><p>${escapeHtml(error.message)}</p></div></td></tr>`;
      showToast(error.message, 'circle-alert');
      refreshIcons();
    }
  }

  function openProductModal(product = null) {
    const form = document.getElementById('productForm');
    form.reset();
    document.getElementById('productFormAlert').classList.remove('show');
    document.getElementById('productId').value = product?._id || '';
    document.getElementById('productModalTitle').textContent = product ? 'Edit product' : 'Add product';
    document.getElementById('productFormEyebrow').textContent = product ? 'Update collection piece' : 'New collection piece';
    if (product) {
      document.getElementById('productName').value = product.name || '';
      document.getElementById('productCategory').value = product.category || 'Essentials';
      document.getElementById('productPrice').value = product.price || '';
      document.getElementById('productComparePrice').value = product.compareAt || '';
      document.getElementById('productStock').value = product.stock ?? 0;
      document.getElementById('productSizes').value = Array.isArray(product.sizes) ? product.sizes.join(', ') : product.sizes || '';
      document.getElementById('productBadge').value = product.badge || '';
      document.getElementById('productImage').value = product.imageUrl || '';
      document.getElementById('productDescription').value = product.description || '';
    }
    document.body.classList.add('no-scroll');
    overlay.classList.add('open');
    modal.classList.add('open');
    modal.setAttribute('aria-hidden', 'false');
    setTimeout(() => document.getElementById('productName').focus(), 100);
  }

  function closeProductModal() {
    document.body.classList.remove('no-scroll');
    overlay.classList.remove('open');
    modal.classList.remove('open');
    modal.setAttribute('aria-hidden', 'true');
  }

  async function saveProduct(event) {
    event.preventDefault();
    if (!event.currentTarget.checkValidity()) {
      event.currentTarget.reportValidity();
      return;
    }
    const id = document.getElementById('productId').value;
    const payload = {
      name: document.getElementById('productName').value.trim(),
      category: document.getElementById('productCategory').value,
      price: Number(document.getElementById('productPrice').value),
      compareAt: Number(document.getElementById('productComparePrice').value || 0),
      stock: Number(document.getElementById('productStock').value || 0),
      sizes: document.getElementById('productSizes').value.split(',').map((size) => size.trim()).filter(Boolean),
      badge: document.getElementById('productBadge').value.trim(),
      imageUrl: document.getElementById('productImage').value.trim(),
      description: document.getElementById('productDescription').value.trim(),
    };
    const button = document.getElementById('saveProductBtn');
    button.disabled = true;
    button.textContent = 'Saving…';
    try {
      await requestJson(id ? `/api/admin/products/${encodeURIComponent(id)}` : '/api/admin/products', {
        method: id ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      closeProductModal();
      showToast(id ? 'Product updated' : 'Product added to the collection');
      await loadData();
    } catch (error) {
      showFormError(error.message);
    } finally {
      button.disabled = false;
      button.textContent = 'Save product';
    }
  }

  async function deleteProduct(product) {
    if (!window.confirm(`Delete “${product.name}”? This cannot be undone.`)) return;
    try {
      await requestJson(`/api/admin/products/${encodeURIComponent(product._id)}`, { method: 'DELETE' });
      showToast('Product removed from the collection');
      await loadData();
    } catch (error) {
      showToast(error.message, 'circle-alert');
    }
  }

  function switchView(view) {
    document.querySelectorAll('[data-admin-view]').forEach((button) => button.classList.toggle('active', button.dataset.adminView === view));
    document.querySelectorAll('.admin-view').forEach((panel) => panel.classList.toggle('active', panel.id === `${view}View`));
    document.getElementById('adminPageTitle').textContent = view === 'orders' ? 'Orders' : 'Inventory';
    document.getElementById('adminPageSubtitle').textContent = view === 'orders'
      ? 'Review the latest purchases from your clients.'
      : 'Manage the pieces customers see in your collection.';
  }

  document.querySelectorAll('[data-admin-view]').forEach((button) => button.addEventListener('click', () => switchView(button.dataset.adminView)));
  document.getElementById('newProductBtn').addEventListener('click', () => openProductModal());
  document.getElementById('productModalClose').addEventListener('click', closeProductModal);
  document.getElementById('cancelProductBtn').addEventListener('click', closeProductModal);
  document.getElementById('productForm').addEventListener('submit', saveProduct);
  document.getElementById('inventorySearch').addEventListener('input', renderInventory);
  overlay.addEventListener('click', closeProductModal);
  document.getElementById('inventoryRows').addEventListener('click', (event) => {
    const edit = event.target.closest('[data-edit-product]');
    const remove = event.target.closest('[data-delete-product]');
    if (edit) openProductModal(products.find((product) => product._id === decodeURIComponent(edit.dataset.editProduct)));
    if (remove) deleteProduct(products.find((product) => product._id === decodeURIComponent(remove.dataset.deleteProduct)));
    if (event.target.closest('#emptyAddProduct')) openProductModal();
  });
  document.getElementById('adminLogout').addEventListener('click', async () => {
    try { await fetch('/api/logout', { method: 'POST', credentials: 'same-origin' }); } finally { window.location.replace('/login'); }
  });
  document.addEventListener('keydown', (event) => { if (event.key === 'Escape') closeProductModal(); });

  (async () => {
    try {
      const user = await requestJson('/api/me');
      document.getElementById('adminName').textContent = user.name || 'Administrator';
      document.getElementById('adminInitials').textContent = (user.name || 'SA').split(' ').map((part) => part[0]).slice(0, 2).join('').toUpperCase();
    } catch {
      return;
    }
    await loadData();
  })();
  refreshIcons();
})();
