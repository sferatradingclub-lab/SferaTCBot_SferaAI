// Основной модуль Telegram Mini App SferaTC.
// Скрипт инициализирует WebApp, обрабатывает навигацию между разделами и добавляет кнопку закрытия.
const resolveTelegramWebApp = () => {
  if (typeof window === 'undefined') {
    return null;
  }

  if (window.Telegram && window.Telegram.WebApp) {
    return window.Telegram.WebApp;
  }

  try {
    if (
      window.parent &&
      window.parent !== window &&
      window.parent.Telegram &&
      window.parent.Telegram.WebApp
    ) {
      return window.parent.Telegram.WebApp;
    }
  } catch (error) {
    console.debug('SferaTC Mini App: не удалось получить Telegram.WebApp у родительского окна.', error);
  }

  return null;
};

const initializeMiniApp = () => {
  const mainMenu = document.getElementById('main-menu');
  const sectionsWrapper = document.getElementById('sections');
  const sectionElements = Array.from(document.querySelectorAll('.section'));
  const backButtons = document.querySelectorAll('.back-btn');
  const closeButton = document.getElementById('btn-close');

  let telegramWebApp = resolveTelegramWebApp();
  let readyCalled = false;

  const applyEnvironmentState = (webAppInstance) => {
    telegramWebApp = webAppInstance;
    const isTelegram = Boolean(webAppInstance);

    document.body.setAttribute('data-app-env', isTelegram ? 'telegram' : 'browser');

    if (isTelegram) {
      if (!readyCalled) {
        try {
          webAppInstance.ready();
          readyCalled = true;
        } catch (error) {
          console.warn('SferaTC Mini App: не удалось вызвать Telegram.WebApp.ready()', error);
        }
      }

      const user = webAppInstance.initDataUnsafe && webAppInstance.initDataUnsafe.user;
      if (user) {
        console.debug('SferaTC Mini App user:', {
          id: user.id,
          username: user.username,
          firstName: user.first_name,
          lastName: user.last_name,
        });
      }
    } else {
      console.warn(
        'SferaTC Mini App: Telegram Web App API не обнаружен. Кнопка "Закрыть" использует window.close().' 
      );
    }
  };

  applyEnvironmentState(telegramWebApp);

  if (!telegramWebApp) {
    window.addEventListener(
      'TelegramWebAppReady',
      () => {
        applyEnvironmentState(resolveTelegramWebApp());
      },
      { once: true }
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
    if (mainMenu) {
      mainMenu.classList.remove('hidden');
    }
    if (sectionsWrapper) {
      sectionsWrapper.classList.remove('visible');
    }
  };

  const openSection = (section) => {
    if (!section) {
      return;
    }

    hideAllSections();
    if (mainMenu) {
      mainMenu.classList.add('hidden');
    }
    if (sectionsWrapper) {
      sectionsWrapper.classList.add('visible');
    }
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
    closeButton.hidden = false;
    closeButton.removeAttribute('hidden');
    closeButton.classList.remove('hidden');
    closeButton.style.display = '';

    closeButton.addEventListener('click', () => {
      const currentWebApp = resolveTelegramWebApp();

      if (currentWebApp && typeof currentWebApp.close === 'function') {
        currentWebApp.close();
      } else {
        try {
          window.close();
        } catch (error) {
          console.warn('SferaTC Mini App: window.close() недоступен в этом окружении.', error);
        }
      }
    });
  }
};

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeMiniApp, { once: true });
} else {
  initializeMiniApp();
}
