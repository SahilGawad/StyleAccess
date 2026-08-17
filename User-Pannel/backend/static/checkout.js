(() => {
  const upiFields = document.getElementById('upiFields');
  const cardFields = document.getElementById('cardFields');
  const codFields = document.getElementById('codFields');
  const upiInput = document.getElementById('upiId');
  const cardNumber = document.getElementById('cardNumber');
  const cardExpiry = document.getElementById('cardExpiry');
  const cardCvv = document.getElementById('cardCvv');

  function refreshIcons() {
    if (window.lucide) window.lucide.createIcons({ attrs: { 'aria-hidden': 'true' } });
  }

  function setPaymentMethod(method) {
    upiFields.hidden = method !== 'upi';
    cardFields.hidden = method !== 'card';
    codFields.hidden = method !== 'cod';
    upiInput.required = method === 'upi';
    cardNumber.required = method === 'card';
    cardExpiry.required = method === 'card';
    cardCvv.required = method === 'card';
  }

  document.querySelectorAll('input[name="payment_method"]').forEach((radio) => {
    radio.addEventListener('change', () => setPaymentMethod(radio.value));
  });

  cardNumber?.addEventListener('input', () => {
    const digits = cardNumber.value.replace(/\D/g, '').slice(0, 16);
    cardNumber.value = digits.replace(/(.{4})/g, '$1 ').trim();
  });

  cardExpiry?.addEventListener('input', () => {
    const digits = cardExpiry.value.replace(/\D/g, '').slice(0, 4);
    cardExpiry.value = digits.length > 2 ? `${digits.slice(0, 2)}/${digits.slice(2)}` : digits;
  });

  cardCvv?.addEventListener('input', () => {
    cardCvv.value = cardCvv.value.replace(/\D/g, '').slice(0, 4);
  });

  upiInput?.addEventListener('input', () => {
    upiInput.setCustomValidity(upiInput.value && !/^[\w.-]+@[\w.-]+$/.test(upiInput.value) ? 'Enter a valid UPI ID, for example name@bank.' : '');
  });

  document.getElementById('checkoutForm')?.addEventListener('submit', (event) => {
    const selectedMethod = document.querySelector('input[name="payment_method"]:checked')?.value;
    if (selectedMethod === 'card' && cardNumber.value.replace(/\D/g, '').length < 12) {
      cardNumber.setCustomValidity('Enter a valid card number.');
      cardNumber.reportValidity();
      event.preventDefault();
      return;
    }
    const button = document.getElementById('placeOrderBtn');
    if (!event.defaultPrevented && event.currentTarget.checkValidity()) {
      button.disabled = true;
      button.textContent = 'Confirming your order…';
    }
  });

  cardNumber?.addEventListener('input', () => cardNumber.setCustomValidity(''));
  setPaymentMethod(document.querySelector('input[name="payment_method"]:checked')?.value || 'upi');
  refreshIcons();
})();
