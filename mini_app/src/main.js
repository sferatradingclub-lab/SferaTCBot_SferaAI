// Основной модуль Telegram Mini App SferaTC.
// Скрипт инициализирует WebApp, обрабатывает навигацию между разделами и добавляет кнопку закрытия.
document.addEventListener('DOMContentLoaded', () => {
  const tg = window.Telegram?.WebApp;
  const mainMenu = document.getElementById('main-menu');
  const sectionElements = Array.from(document.querySelectorAll('.section'));
  const backButtons = document.querySelectorAll('.back-btn');
  const closeButton = document.getElementById('btn-close');

  if (tg) {
    tg.ready();
    const user = tg.initDataUnsafe?.user;
    if (user) {
      // Пользовательские данные будут использованы в будущих версиях интерфейса.
      console.debug('SferaTC Mini App user:', {
        id: user.id,
        username: user.username,
        firstName: user.first_name,
        lastName: user.last_name,
      });
    }
  } else {
    console.warn(
      'Не удалось инициализировать Telegram Web App. Откройте Mini App внутри Telegram для полного функционала.'
    );
  }

  const sectionsMap = {
    screener: document.getElementById('section-screener'),
    news: document.getElementById('section-news'),
    analyst: document.getElementById('section-analyst'),
    game: document.getElementById('section-game'),
  };

  const hideAllSections = () => {
    sectionElements.forEach((section) => section.classList.remove('active'));
  };

  const showMainMenu = () => {
    hideAllSections();
    mainMenu?.classList.remove('hidden');
  };

  const openSection = (section) => {
    if (!section) {
      return;
    }

    hideAllSections();
    mainMenu?.classList.add('hidden');
    section.classList.add('active');
  };

  const navButtonsConfig = [
    { buttonId: 'btn-screener', sectionKey: 'screener' },
    { buttonId: 'btn-news', sectionKey: 'news' },
    { buttonId: 'btn-analyst', sectionKey: 'analyst' },
    { buttonId: 'btn-game', sectionKey: 'game' },
  ];

  navButtonsConfig.forEach(({ buttonId, sectionKey }) => {
    const button = document.getElementById(buttonId);
    const section = sectionsMap[sectionKey];

    if (button && section) {
      button.addEventListener('click', () => openSection(section));
    }
  });

  backButtons.forEach((button) => {
    button.addEventListener('click', () => {
      showMainMenu();
    });
  });

  if (closeButton) {
    closeButton.addEventListener('click', () => {
      if (tg && typeof tg.close === 'function') {
        tg.close();
      } else {
        window.close();
      }
    });
  }
});
