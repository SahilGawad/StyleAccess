(() => {
  const productDataNode = document.getElementById('initialProducts');
  let products = [];
  try {
    products = productDataNode ? JSON.parse(productDataNode.textContent || '[]') : [];
  } catch {
    products = [];
  }

  const state = {
    filter: 'All',
    sort: 'featured',
    wishlistOnly: false,
    activeProduct: null,
    selectedSize: null,
    wishlist: new Set(JSON.parse(localStorage.getItem('styleaccess-wishlist') || '[]')),
  };

  const fallbackImage = '/static/images/regent-blazer.jpg';
  const productGrid = document.getElementById('productGrid');
  const filterChips = document.getElementById('filterChips');
  const productSort = document.getElementById('productSort');
  const resultsCopy = document.getElementById('resultsCopy');
  const overlay = document.getElementById('overlay');
  const cartDrawer = document.getElementById('cartDrawer');
  const quickViewModal = document.getElementById('quickViewModal');
  let toastTimer;

  const money = (value) => new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(Number(value) || 0);

  const escapeHtml = (value = '') => String(value).replace(/[&<>'"]/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;',
  }[char]));

  const productId = (product) => String(product._id || product.name);
  const getProduct = (encodedId) => {
    const id = decodeURIComponent(encodedId || '');
    return products.find((product) => productId(product) === id);
  };

  function refreshIcons() {
    if (window.lucide) window.lucide.createIcons({ attrs: { 'aria-hidden': 'true' } });
  }

  function showToast(message, icon = 'check-circle') {
    const toast = document.getElementById('toast');
    const text = document.getElementById('toastText');
    if (!toast || !text) return;
    toast.querySelector('svg')?.remove();
    const iconNode = document.createElement('i');
    iconNode.setAttribute('data-lucide', icon);
    toast.prepend(iconNode);
    text.textContent = message;
    refreshIcons();
    toast.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove('show'), 2800);
  }

  function updateWishlistCount() {
    const count = document.getElementById('wishlistCount');
    if (!count) return;
    count.textContent = state.wishlist.size;
    count.hidden = state.wishlist.size === 0;
  }

  function saveWishlist() {
    localStorage.setItem('styleaccess-wishlist', JSON.stringify([...state.wishlist]));
    updateWishlistCount();
  }

  function createProductCard(product) {
    const id = encodeURIComponent(productId(product));
    const saved = state.wishlist.has(productId(product));
    const comparePrice = Number(product.compareAt) > Number(product.price)
      ? `<s>${money(product.compareAt)}</s>` : '';
    const badge = product.badge ? `<span class="product-badge">${escapeHtml(product.badge)}</span>` : '';
    return `
      <article class="product-card" data-product-id="${id}">
        <div class="product-media">
          <img src="${escapeHtml(product.imageUrl || fallbackImage)}" alt="${escapeHtml(product.name)}" loading="lazy" onerror="this.onerror=null;this.src='${fallbackImage}'">
          ${badge}
          <button class="wishlist-btn ${saved ? 'active' : ''}" type="button" data-wishlist-id="${id}" aria-label="${saved ? 'Remove' : 'Save'} ${escapeHtml(product.name)}">
            <i data-lucide="heart"></i>
          </button>
          <button class="quick-view-btn" type="button" data-quick-view-id="${id}">Quick view</button>
        </div>
        <div class="product-info">
          <div class="product-meta">
            <span>${escapeHtml(product.category || 'Essentials')}</span>
            <span class="rating"><i data-lucide="star"></i> ${Number(product.rating || 4.8).toFixed(1)}</span>
          </div>
          <h3 class="product-name">${escapeHtml(product.name)}</h3>
          <div class="product-price"><span>${money(product.price)}</span>${comparePrice}</div>
          <div class="product-card-actions">
            <button class="btn add-cart-btn" type="button" data-add-cart-id="${id}" ${Number(product.stock) === 0 ? 'disabled' : ''}>${Number(product.stock) === 0 ? 'Sold out' : 'Add to bag'}</button>
            <button class="btn buy-now-btn" type="button" data-buy-now-id="${id}" aria-label="Buy ${escapeHtml(product.name)} now" ${Number(product.stock) === 0 ? 'disabled' : ''}>
              <i data-lucide="zap"></i>
            </button>
          </div>
        </div>
      </article>`;
  }

  function visibleProducts() {
    let visible = [...products];
    if (state.wishlistOnly) {
      visible = visible.filter((product) => state.wishlist.has(productId(product)));
    } else if (state.filter !== 'All') {
      visible = visible.filter((product) => product.category === state.filter);
    }
    if (state.sort === 'price-low') visible.sort((a, b) => Number(a.price) - Number(b.price));
    if (state.sort === 'price-high') visible.sort((a, b) => Number(b.price) - Number(a.price));
    if (state.sort === 'rating') visible.sort((a, b) => Number(b.rating) - Number(a.rating));
    if (state.sort === 'newest') visible.reverse();
    return visible;
  }

  function renderProducts() {
    if (!productGrid) return;
    const visible = visibleProducts();
    productGrid.innerHTML = visible.length
      ? visible.map(createProductCard).join('')
      : `<div class="empty-products"><i data-lucide="heart-off"></i><h3>${state.wishlistOnly ? 'No saved pieces yet' : 'No pieces found'}</h3><p>${state.wishlistOnly ? 'Use the heart on any piece to keep it here.' : 'Try another collection.'}</p><button class="btn btn-outline" id="resetProducts" type="button">View all pieces</button></div>`;
    if (resultsCopy) resultsCopy.textContent = `${visible.length} ${visible.length === 1 ? 'piece' : 'pieces'}`;
    refreshIcons();
  }

  function setCategory(category) {
    state.wishlistOnly = false;
    state.filter = category;
    filterChips?.querySelectorAll('.filter-chip').forEach((chip) => {
      chip.classList.toggle('active', chip.dataset.category === category);
    });
    renderProducts();
  }

  function buildFilters() {
    if (!filterChips) return;
    const categories = ['All', ...new Set(products.map((product) => product.category || 'Essentials'))];
    filterChips.innerHTML = categories.map((category) => `
      <button class="filter-chip ${category === state.filter ? 'active' : ''}" type="button" data-category="${escapeHtml(category)}">${escapeHtml(category)}</button>
    `).join('');
  }

  function toggleWishlist(product) {
    const id = productId(product);
    if (state.wishlist.has(id)) {
      state.wishlist.delete(id);
      showToast(`${product.name} removed from saved pieces`, 'heart');
    } else {
      state.wishlist.add(id);
      showToast(`${product.name} saved for later`, 'heart');
    }
    saveWishlist();
    renderProducts();
  }

  function openOverlayPanel(panel) {
    document.body.classList.add('no-scroll');
    overlay?.classList.add('open');
    panel?.classList.add('open');
    panel?.setAttribute('aria-hidden', 'false');
  }

  function closePanels() {
    document.body.classList.remove('no-scroll');
    overlay?.classList.remove('open');
    cartDrawer?.classList.remove('open');
    cartDrawer?.setAttribute('aria-hidden', 'true');
    quickViewModal?.classList.remove('open');
    quickViewModal?.setAttribute('aria-hidden', 'true');
  }

  function openQuickView(product) {
    if (!quickViewModal || !product) return;
    state.activeProduct = product;
    state.selectedSize = null;
    const image = document.getElementById('quickViewImage');
    image.src = product.imageUrl || fallbackImage;
    image.alt = product.name;
    image.onerror = () => { image.src = fallbackImage; };
    document.getElementById('quickViewCategory').textContent = product.category || 'Essentials';
    document.getElementById('quickViewName').textContent = product.name;
    document.getElementById('quickViewPrice').innerHTML = `${money(product.price)}${Number(product.compareAt) > Number(product.price) ? ` <s>${money(product.compareAt)}</s>` : ''}`;
    document.getElementById('quickViewRating').textContent = Number(product.rating || 4.8).toFixed(1);
    document.getElementById('quickViewDescription').textContent = product.description || 'A refined StyleAccess essential, made for repeat wear.';
    const sizes = Array.isArray(product.sizes) ? product.sizes : String(product.sizes || 'One size').split(',');
    document.getElementById('sizeOptions').innerHTML = sizes.map((size) => `<button type="button" class="size-option" data-size="${escapeHtml(String(size).trim())}">${escapeHtml(String(size).trim())}</button>`).join('');
    const addButton = document.getElementById('quickAddBtn');
    addButton.disabled = Number(product.stock) === 0;
    addButton.textContent = Number(product.stock) === 0 ? 'Currently sold out' : 'Select a size';
    openOverlayPanel(quickViewModal);
    refreshIcons();
  }

  async function requestJson(url, options = {}) {
    const response = await fetch(url, { credentials: 'same-origin', ...options });
    const contentType = response.headers.get('content-type') || '';
    const data = contentType.includes('application/json') ? await response.json() : {};
    if (!response.ok) throw new Error(data.error || 'Something went wrong. Please try again.');
    return data;
  }

  async function addToCart(product, showBag = false) {
    try {
      const summary = await requestJson('/add_to_cart', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: product.name }),
      });
      updateCartCount(summary.count);
      showToast(`${product.name} added to your bag`);
      closePanels();
      if (showBag) await openCart();
    } catch (error) {
      showToast(error.message, 'circle-alert');
    }
  }

  async function buyNow(product) {
    try {
      const data = await requestJson('/buy_now', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: product.name }),
      });
      window.location.href = data.redirect || '/payment';
    } catch (error) {
      showToast(error.message, 'circle-alert');
    }
  }

  function updateCartCount(count) {
    const cartCount = document.getElementById('cartCount');
    const drawerCount = document.getElementById('drawerCount');
    if (cartCount) cartCount.textContent = count || 0;
    if (drawerCount) drawerCount.textContent = `(${count || 0})`;
  }

  function renderCart(summary) {
    const cartItems = document.getElementById('cartItems');
    const cartFooter = document.getElementById('cartFooter');
    if (!cartItems || !cartFooter) return;
    updateCartCount(summary.count);
    if (!summary.items?.length) {
      cartItems.innerHTML = `<div class="cart-empty"><div><i data-lucide="shopping-bag"></i><p>Your bag is waiting for something special.</p><button class="btn btn-outline" type="button" id="drawerShopBtn">Continue shopping</button></div></div>`;
      cartFooter.hidden = true;
      refreshIcons();
      return;
    }
    cartItems.innerHTML = summary.items.map((item) => {
      const name = encodeURIComponent(item.name);
      return `<article class="cart-line">
        <img src="${escapeHtml(item.imageUrl || fallbackImage)}" alt="${escapeHtml(item.name)}" onerror="this.onerror=null;this.src='${fallbackImage}'">
        <div>
          <p>${escapeHtml(item.category || 'StyleAccess')}</p>
          <h3>${escapeHtml(item.name)}</h3>
          <strong>${money(item.price)}</strong>
          <div class="quantity-control" aria-label="Quantity for ${escapeHtml(item.name)}">
            <button type="button" data-cart-action="decrease" data-cart-name="${name}" aria-label="Decrease quantity">−</button>
            <span>${item.qty}</span>
            <button type="button" data-cart-action="increase" data-cart-name="${name}" aria-label="Increase quantity">+</button>
          </div>
        </div>
        <button class="remove-line" type="button" data-cart-remove="${name}" aria-label="Remove ${escapeHtml(item.name)}"><i data-lucide="trash-2"></i></button>
      </article>`;
    }).join('');
    document.getElementById('cartTotal').textContent = money(summary.total);
    cartFooter.hidden = false;
    refreshIcons();
  }

  async function openCart() {
    openOverlayPanel(cartDrawer);
    const cartItems = document.getElementById('cartItems');
    if (cartItems) cartItems.innerHTML = '<div class="cart-empty"><div><i data-lucide="loader-circle"></i><p>Preparing your bag…</p></div></div>';
    refreshIcons();
    try {
      renderCart(await requestJson('/api/cart'));
    } catch (error) {
      if (cartItems) cartItems.innerHTML = `<div class="cart-empty"><p>${escapeHtml(error.message)}</p></div>`;
    }
  }

  async function updateCartItem(name, action) {
    try {
      const summary = await requestJson(action === 'remove' ? '/remove_item' : '/update_cart', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(action === 'remove' ? { name } : { name, action }),
      });
      renderCart(summary);
    } catch (error) {
      showToast(error.message, 'circle-alert');
    }
  }

  function setupHeader() {
    const menuButton = document.getElementById('mobileMenuBtn');
    const nav = document.getElementById('mainNav');
    const searchToggle = document.getElementById('searchToggle');
    const searchPanel = document.getElementById('searchPanel');
    menuButton?.addEventListener('click', () => {
      const open = nav?.classList.toggle('open');
      menuButton.setAttribute('aria-expanded', String(Boolean(open)));
      menuButton.innerHTML = `<i data-lucide="${open ? 'x' : 'menu'}"></i>`;
      refreshIcons();
    });
    searchToggle?.addEventListener('click', () => {
      const open = searchPanel?.classList.toggle('open');
      searchToggle.setAttribute('aria-expanded', String(Boolean(open)));
      if (open) setTimeout(() => document.getElementById('siteSearch')?.focus(), 120);
    });
  }

  function setupCatalog() {
    if (!productGrid) return;
    buildFilters();
    const pendingCategory = sessionStorage.getItem('styleaccess-category');
    const pendingWishlist = sessionStorage.getItem('styleaccess-wishlist-view');
    if (pendingCategory && products.some((product) => product.category === pendingCategory)) {
      state.filter = pendingCategory;
      sessionStorage.removeItem('styleaccess-category');
      buildFilters();
    }
    if (pendingWishlist) {
      state.wishlistOnly = true;
      sessionStorage.removeItem('styleaccess-wishlist-view');
    }
    renderProducts();
    filterChips?.addEventListener('click', (event) => {
      const chip = event.target.closest('[data-category]');
      if (chip) setCategory(chip.dataset.category);
    });
    productSort?.addEventListener('change', () => {
      state.sort = productSort.value;
      renderProducts();
    });
    productGrid.addEventListener('click', (event) => {
      const wishlist = event.target.closest('[data-wishlist-id]');
      const quickView = event.target.closest('[data-quick-view-id]');
      const add = event.target.closest('[data-add-cart-id]');
      const buy = event.target.closest('[data-buy-now-id]');
      const reset = event.target.closest('#resetProducts');
      if (wishlist) toggleWishlist(getProduct(wishlist.dataset.wishlistId));
      if (quickView) openQuickView(getProduct(quickView.dataset.quickViewId));
      if (add) addToCart(getProduct(add.dataset.addCartId));
      if (buy) buyNow(getProduct(buy.dataset.buyNowId));
      if (reset) setCategory('All');
    });
  }

  function setupCrossPageLinks() {
    document.querySelectorAll('[data-category-link]').forEach((link) => {
      link.addEventListener('click', (event) => {
        const category = link.dataset.categoryLink;
        if (productGrid) {
          event.preventDefault();
          setCategory(category);
          document.getElementById('shop')?.scrollIntoView({ behavior: 'smooth' });
        } else {
          sessionStorage.setItem('styleaccess-category', category);
        }
      });
    });
    document.getElementById('wishlistTrigger')?.addEventListener('click', () => {
      if (!productGrid) {
        sessionStorage.setItem('styleaccess-wishlist-view', '1');
        window.location.href = '/#shop';
        return;
      }
      state.wishlistOnly = true;
      filterChips?.querySelectorAll('.filter-chip').forEach((chip) => chip.classList.remove('active'));
      renderProducts();
      document.getElementById('shop')?.scrollIntoView({ behavior: 'smooth' });
    });
    document.getElementById('accountWishlist')?.addEventListener('click', (event) => {
      event.preventDefault();
      sessionStorage.setItem('styleaccess-wishlist-view', '1');
      window.location.href = '/#shop';
    });
  }

  function setupQuickView() {
    document.getElementById('sizeOptions')?.addEventListener('click', (event) => {
      const option = event.target.closest('[data-size]');
      if (!option) return;
      state.selectedSize = option.dataset.size;
      document.querySelectorAll('.size-option').forEach((button) => button.classList.toggle('active', button === option));
      document.getElementById('quickAddBtn').textContent = 'Add to bag';
    });
    document.getElementById('quickAddBtn')?.addEventListener('click', () => {
      if (!state.selectedSize) {
        showToast('Please choose your size first', 'ruler');
        return;
      }
      addToCart(state.activeProduct);
    });
  }

  function setupNewsletter() {
    document.getElementById('newsletterForm')?.addEventListener('submit', (event) => {
      event.preventDefault();
      const email = document.getElementById('newsletterEmail').value.trim();
      localStorage.setItem('styleaccess-newsletter-email', email);
      event.currentTarget.reset();
      showToast('You’re on the private list. Welcome.');
    });
  }

  document.addEventListener('click', (event) => {
    const indexedWishlist = event.target.closest('[data-wishlist-index]');
    const indexedQuickView = event.target.closest('[data-quick-view]');
    const indexedAdd = event.target.closest('[data-add-cart]');
    const indexedBuy = event.target.closest('[data-buy-now]');
    if (indexedWishlist) toggleWishlist(products[Number(indexedWishlist.dataset.wishlistIndex)]);
    if (indexedQuickView) openQuickView(products[Number(indexedQuickView.dataset.quickView)]);
    if (indexedAdd) addToCart(products[Number(indexedAdd.dataset.addCart)]);
    if (indexedBuy) buyNow(products[Number(indexedBuy.dataset.buyNow)]);
  });

  document.getElementById('cartTrigger')?.addEventListener('click', openCart);
  document.getElementById('cartClose')?.addEventListener('click', closePanels);
  document.getElementById('quickViewClose')?.addEventListener('click', closePanels);
  overlay?.addEventListener('click', closePanels);
  document.getElementById('cartItems')?.addEventListener('click', (event) => {
    const action = event.target.closest('[data-cart-action]');
    const remove = event.target.closest('[data-cart-remove]');
    if (action) updateCartItem(decodeURIComponent(action.dataset.cartName), action.dataset.cartAction);
    if (remove) updateCartItem(decodeURIComponent(remove.dataset.cartRemove), 'remove');
    if (event.target.closest('#drawerShopBtn')) closePanels();
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') closePanels();
  });

  setupHeader();
  setupCatalog();
  setupCrossPageLinks();
  setupQuickView();
  setupNewsletter();
  updateWishlistCount();
  refreshIcons();
})();
