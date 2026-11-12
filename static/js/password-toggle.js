(() => {
  const input = document.querySelector('.auth-form input[type="password"]');
  if (!input || input.closest('.auth-password')) return;
  const wrapper = document.createElement('div');
  wrapper.className = 'auth-password';
  input.before(wrapper);
  wrapper.append(input);
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'password-toggle';
  button.textContent = 'Show';
  button.setAttribute('aria-label', 'Show password');
  button.setAttribute('aria-controls', input.id);
  button.setAttribute('aria-pressed', 'false');
  button.addEventListener('click', () => {
    const visible = input.type === 'password';
    input.type = visible ? 'text' : 'password';
    button.textContent = visible ? 'Hide' : 'Show';
    button.setAttribute('aria-label', visible ? 'Hide password' : 'Show password');
    button.setAttribute('aria-pressed', String(visible));
  });
  wrapper.append(button);
})();
