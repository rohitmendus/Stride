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
  button.innerHTML = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/><path class="password-slash" d="m3 3 18 18"/></svg>';
  button.setAttribute('aria-label', 'Show password');
  button.setAttribute('aria-controls', input.id);
  button.setAttribute('aria-pressed', 'false');
  button.addEventListener('click', () => {
    const visible = input.type === 'password';
    input.type = visible ? 'text' : 'password';

    button.setAttribute('aria-label', visible ? 'Hide password' : 'Show password');
    button.setAttribute('aria-pressed', String(visible));
  });
  wrapper.append(button);
})();
