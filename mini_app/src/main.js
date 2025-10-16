// Основной модуль Telegram Mini App SferaTC.
// Скрипт инициализирует WebApp, выводит данные пользователя и добавляет кнопку закрытия.
document.addEventListener('DOMContentLoaded', () => {
  const tg = window.Telegram?.WebApp; // Главный объект Telegram Web App API.
  const appContainer = document.getElementById('app');
  const userInfoContainer = document.getElementById('user-info');

  if (!tg) {
    userInfoContainer.textContent =
      'Не удалось инициализировать Telegram Web App. Откройте Mini App внутри Telegram.';
    return;
  }

  tg.ready();

  const user = tg.initDataUnsafe?.user;

  if (user) {
    const username = user.username ? `@${user.username}` : '—';

    userInfoContainer.innerHTML = `
      <p><strong>ID:</strong> ${user.id}</p>
      <p><strong>Имя:</strong> ${user.first_name ?? '—'}</p>
      <p><strong>Username:</strong> ${username}</p>
    `;
  } else {
    userInfoContainer.textContent =
      'Данные пользователя недоступны. Убедитесь, что вы открыли приложение через Telegram.';
  }

  const closeButton = document.createElement('button');
  closeButton.type = 'button';
  closeButton.textContent = 'Закрыть приложение';
  closeButton.addEventListener('click', () => tg.close());

  appContainer.appendChild(closeButton);
});
