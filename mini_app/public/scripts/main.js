// Проверка Telegram API сразу, до DOMContentLoaded
const tg = window.Telegram?.WebApp;
const isTelegram = !!tg;

console.log('Telegram WebApp:', tg); // Для отладки
console.log('isTelegram:', isTelegram); // Для отладки

document.addEventListener('DOMContentLoaded', () => {
  // Прячем кнопку "Закрыть" в Telegram, показываем в браузере
  const closeBtn = document.getElementById('btn-close');
  if (closeBtn) {
    if (isTelegram) {
      closeBtn.style.display = 'none';
      console.log('Кнопка "Закрыть" скрыта в Telegram');
    } else {
      closeBtn.style.display = 'block';
      console.log('Кнопка "Закрыть" показана в браузере');
    }
  }

  if (isTelegram) {
    tg.ready();
  }

 const mainMenu = document.getElementById('main-menu');
  const sectionsWrapper = document.getElementById('sections');
  
  const sectionMap = {
    'btn-screener': 'section-screener',
    'btn-news': 'section-news',
    'btn-analyst': 'section-analyst',
    'btn-game': 'section-game',
  };

  const showSection = (sectionId) => {
    const section = document.getElementById(sectionId);
    if (!section) return;

    mainMenu.classList.add('hidden');
    sectionsWrapper.classList.add('visible');
    section.classList.add('active');
  };

  const showMenu = () => {
    mainMenu.classList.remove('hidden');
    sectionsWrapper.classList.remove('visible');
    sectionsWrapper.querySelectorAll('.section.active').forEach(s => s.classList.remove('active'));
  };

  Object.entries(sectionMap).forEach(([buttonId, sectionId]) => {
    const button = document.getElementById(buttonId);
    if (button) {
      button.addEventListener('click', () => showSection(sectionId));
      // Добавь touch-события для Telegram
      button.addEventListener('touchstart', () => button.classList.add('active'));
      button.addEventListener('touchend', () => button.classList.remove('active'));
    }
  });

  sectionsWrapper.querySelectorAll('.back-btn').forEach(button => {
    button.addEventListener('click', showMenu);
  });

  document.getElementById('btn-close')?.addEventListener('click', () => {
    if (isTelegram) {
      tg.close();
    } else {
      window.close(); // Или alert для браузера
    }
 });
});
