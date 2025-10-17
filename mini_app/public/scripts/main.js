document.addEventListener('DOMContentLoaded', () => {
  // Ждем полной загрузки DOM
  const mainMenu = document.getElementById('main-menu');
  const sectionsWrapper = document.getElementById('sections');
  const closeButton = document.getElementById('btn-close');

  if (!mainMenu || !closeButton) {
    console.error('SferaTC Mini App: Критические элементы DOM не найдены.');
    return;
  }

  const sectionMap = {
    'btn-screener': 'section-screener',
    'btn-news': 'section-news',
    'btn-analyst': 'section-analyst',
    'btn-game': 'section-game',
  };

  // Функция для безопасного получения WebApp
  const getTelegramWebApp = () => {
    try {
      if (window.Telegram && window.Telegram.WebApp) {
        return window.Telegram.WebApp;
      }
      if (window.parent && window.parent.Telegram && window.parent.Telegram.WebApp) {
        return window.parent.Telegram.WebApp;
      }
    } catch (e) {
      console.debug('SferaTC Mini App: Не удалось получить WebApp из родительского окна.');
    }
    return null;
  };

  let webApp = getTelegramWebApp();

  // Если WebApp еще не загружен, ждем события
  if (!webApp) {
    window.addEventListener('TelegramWebAppReady', () => {
      webApp = getTelegramWebApp();
      console.log('SferaTC Mini App: Telegram WebApp API готов.');
    }, { once: true });
  } else {
    console.log('SferaTC Mini App: Telegram WebApp API уже загружен.');
  }

  // Показываем, что мы в Telegram
  if (webApp) {
    document.body.setAttribute('data-app-env', 'telegram');
    try {
      webApp.ready();
      console.log('SferaTC Mini App: webApp.ready() вызван.');
    } catch (e) {
      console.warn('SferaTC Mini App: Не удалось вызвать webApp.ready().', e);
    }
  } else {
    document.body.setAttribute('data-app-env', 'browser');
    console.warn('SferaTC Mini App: Telegram WebApp API не найден. Кнопка "Закрыть" будет использовать window.close().');
  }

  // Логика навигации
  const showSection = (sectionId) => {
    const section = document.getElementById(sectionId);
    if (!section || !mainMenu || !sectionsWrapper) return;
    mainMenu.classList.add('hidden');
    sectionsWrapper.classList.add('visible');
    section.classList.add('active');
  };

  const showMenu = () => {
    if (!mainMenu || !sectionsWrapper) return;
    mainMenu.classList.remove('hidden');
    sectionsWrapper.classList.remove('visible');
    sectionsWrapper.querySelectorAll('.section.active').forEach(s => s.classList.remove('active'));
  };

  // Обработчики для кнопок меню
  Object.entries(sectionMap).forEach(([buttonId, sectionId]) => {
    const button = document.getElementById(buttonId);
    if (button) {
      button.addEventListener('click', () => showSection(sectionId));
    }
  });

  // Обработчики для кнопок "Назад"
  sectionsWrapper?.querySelectorAll('.back-btn').forEach(button => {
    button.addEventListener('click', showMenu);
  });

  // Обработчик для кнопки "Закрыть" - САМАЯ ВАЖНАЯ ЧАСТЬ
  if (closeButton) {
    console.log('SferaTC Mini App: Кнопка "Закрыть" найдена. Добавляем обработчик.');
    closeButton.addEventListener('click', () => {
      const currentWebApp = getTelegramWebApp();
      if (currentWebApp && typeof currentWebApp.close === 'function') {
        console.log('SferaTC Mini App: Вызов currentWebApp.close()');
        currentWebApp.close();
      } else {
        console.log('SferaTC Mini App: Попытка вызвать window.close()');
        try {
          window.close();
        } catch (error) {
          console.error('SferaTC Mini App: window.close() недоступен.', error);
          alert('Не удалось закрыть приложение. Пожалуйста, используйте кнопку возврата в Telegram.');
        }
      }
    });
  } else {
    console.error('SferaTC Mini App: Кнопка "Закрыть" НЕ найдена!');
  }
});
