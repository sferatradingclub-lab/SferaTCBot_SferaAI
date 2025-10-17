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
    console.debug('SferaTC Mini App: не удалось получить Telegram.WebApp из родительского окна.', error);
  }

  return null;
};

document.addEventListener('DOMContentLoaded', () => {
  const mainMenu = document.getElementById('main-menu');
  const sectionsWrapper = document.getElementById('sections');
  const closeButton = document.getElementById('btn-close');

  const sectionMap = {
    'btn-screener': 'section-screener',
    'btn-news': 'section-news',
    'btn-analyst': 'section-analyst',
    'btn-game': 'section-game',
  };

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

  const showSection = (sectionId) => {
    const section = document.getElementById(sectionId);
    if (!section || !mainMenu || !sectionsWrapper) {
      return;
    }

    mainMenu.classList.add('hidden');
    sectionsWrapper.classList.add('visible');
    section.classList.add('active');
  };

  const showMenu = () => {
    if (!mainMenu || !sectionsWrapper) {
      return;
    }

    mainMenu.classList.remove('hidden');
    sectionsWrapper.classList.remove('visible');
    sectionsWrapper.querySelectorAll('.section.active').forEach((section) => {
      section.classList.remove('active');
    });
  };

  Object.entries(sectionMap).forEach(([buttonId, sectionId]) => {
    const button = document.getElementById(buttonId);
    if (button) {
      button.addEventListener('click', () => showSection(sectionId));
      button.addEventListener('touchstart', () => button.classList.add('active'));
      button.addEventListener('touchend', () => button.classList.remove('active'));
    }
  });

  if (sectionsWrapper) {
    sectionsWrapper.querySelectorAll('.back-btn').forEach((button) => {
      button.addEventListener('click', showMenu);
    });
  }

  if (closeButton) {
    closeButton.hidden = false;
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
});
