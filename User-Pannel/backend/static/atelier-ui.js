(() => {
  const header = document.querySelector('.site-header');
  const onScroll = () => header?.classList.toggle('scrolled', window.scrollY > 24);
  onScroll();
  window.addEventListener('scroll', onScroll, { passive: true });

  const revealTargets = document.querySelectorAll([
    '.section-heading',
    '.collection-card',
    '.product-card',
    '.story-copy > *',
    '.category-tile',
    '.checkout-card',
    '.stat-card',
  ].join(','));

  if (!('IntersectionObserver' in window) || window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    revealTargets.forEach((element) => element.classList.add('atelier-visible'));
    return;
  }

  revealTargets.forEach((element) => element.classList.add('atelier-reveal'));
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add('atelier-visible');
      observer.unobserve(entry.target);
    });
  }, { threshold: .12, rootMargin: '0px 0px -35px' });
  revealTargets.forEach((element) => observer.observe(element));
})();
