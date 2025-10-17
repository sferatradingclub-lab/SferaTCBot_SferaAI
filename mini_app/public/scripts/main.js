/**
 * Main interaction logic for the SferaTC Mini App.
 * Handles Telegram WebApp initialisation and navigation
 * between main menu and feature placeholders.
 */
document.addEventListener('DOMContentLoaded', () => {
  const tg = window.Telegram?.WebApp;

  if (tg) {
    tg.ready();
  }

  const mainMenu = document.getElementById('main-menu');
  const sectionsWrapper = document.getElementById('sections');
  const sectionElements = Array.from(sectionsWrapper.querySelectorAll('.section'));

  const sectionMap = {
    'btn-screener': 'section-screener',
    'btn-news': 'section-news',
    'btn-analyst': 'section-analyst',
    'btn-game': 'section-game',
  };

  const hideSections = () => {
    sectionElements.forEach((section) => section.classList.remove('active'));
    sectionsWrapper.classList.remove('visible');
  };

  const showSection = (sectionId) => {
    const section = document.getElementById(sectionId);

    if (!section) {
      return;
    }

    hideSections();
    section.classList.add('active');
    sectionsWrapper.classList.add('visible');
    mainMenu.classList.add('hidden');
  };

  const showMenu = () => {
    hideSections();
    mainMenu.classList.remove('hidden');
  };

  Object.entries(sectionMap).forEach(([buttonId, sectionId]) => {
    const button = document.getElementById(buttonId);
    if (!button) {
      return;
    }

    button.addEventListener('click', () => {
      showSection(sectionId);
    });
  });

  const backButtons = sectionsWrapper.querySelectorAll('.back-btn');
  backButtons.forEach((button) => {
    button.addEventListener('click', showMenu);
  });

  const closeButton = document.getElementById('btn-close');
  if (closeButton) {
    closeButton.addEventListener('click', () => {
      if (tg) {
        tg.close();
      } else {
        window.close();
      }
    });
  }
});
