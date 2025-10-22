// Простое приложение с нуля
document.addEventListener('DOMContentLoaded', () => {
  // Обработчики для кнопок главного меню
  document.querySelectorAll('.button--menu').forEach(button => {
    button.addEventListener('click', (e) => {
      const section = e.target.dataset.section || e.target.closest('.button--menu').dataset.section;
      showSection(section);
    });
  });

  // Обработчик для кнопки "Закрыть"
  document.querySelectorAll('.button--back').forEach(button => {
    button.addEventListener('click', () => {
      showMainMenu();
    });
  });

  // Функция показа главного меню
  function showMainMenu() {
    // Убираем класс состояния у основного контейнера
    document.querySelector('.app').classList.remove('app-section-open');
    
    // Скрываем все секции
    document.querySelectorAll('.section').forEach(section => {
      section.style.display = 'none';
      section.classList.remove('active');
    });

    // Показываем главное меню
    const mainMenu = document.getElementById('main-menu');
    if (mainMenu) {
      mainMenu.style.display = 'flex';
    }
  }

  // Функция показа секции
  function showSection(sectionName) {
    // Добавляем класс состояния у основного контейнера
    document.querySelector('.app').classList.add('app-section-open');
    
    // Скрываем главное меню
    const mainMenu = document.getElementById('main-menu');
    if (mainMenu) {
      mainMenu.style.display = 'none';
    }

    // Скрываем все секции
    document.querySelectorAll('.section').forEach(section => {
      section.style.display = 'none';
      section.classList.remove('active');
    });

    // Показываем выбранную секцию
    const sectionElement = document.getElementById(`section-${sectionName}`);
    if (sectionElement) {
      sectionElement.style.display = 'block'; // используем block вместо flex, чтобы соответствовать CSS
      // также добавим класс для анимации
      sectionElement.classList.add('active');
    }
  }

  // Изначально показываем главное меню
  showMainMenu();
});
