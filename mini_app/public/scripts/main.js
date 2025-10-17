document.addEventListener('DOMContentLoaded', () => {
  const tg = window.Telegram?.WebApp;
  if (tg) tg.ready();

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
    document.getElementById(buttonId)?.addEventListener('click', () => showSection(sectionId));
  });

  sectionsWrapper.querySelectorAll('.back-btn').forEach(button => {
    button.addEventListener('click', showMenu);
  });

  document.getElementById('btn-close')?.addEventListener('click', () => tg?.close());
});
