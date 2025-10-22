import DOMUtils from '../utils/dom.js';
import EventSystem from './eventSystem.js';
import appConfig from '../config.js';

// Простой модуль навигации
class NavigationModule {
  constructor(stateManager, eventSystem, telegramModule) {
    this.stateManager = stateManager;
    this.eventSystem = eventSystem;
    this.telegramModule = telegramModule;
    this.elements = {};
    this.isInitialized = false;
  }
  
  init() {
    try {
      this.setupElements();
      this.setupEventListeners();
      this.setupInitialState();
      this.setupAccessibility();
      
      this.isInitialized = true;
      console.log('✅ Модуль навигации инициализирован');
      return true;
    } catch (error) {
      console.error('❌ Ошибка инициализации модуля навигации:', error);
      return false;
    }
  }
  
  setupElements() {
    this.elements = {
      mainMenu: DOMUtils.getElement('main-menu'),
      menuButtons: DOMUtils.getElements('.button--menu'),
      sectionsContainer: DOMUtils.getElement('sections-container'),
      app: DOMUtils.getElement('app'),
      backButtons: DOMUtils.getElements('.button--back'),
      sections: DOMUtils.getElements('.section')
    };
  }
  
  setupEventListeners() {
    // Обработчики для кнопок навигации
    this.elements.menuButtons.forEach(button => {
      const sectionKey = button.dataset.section;
      if (sectionKey) {
        DOMUtils.addEventListener(button, 'click', () => {
          this.showSection(sectionKey);
        });
      }
    });
    
    // Обработчики для кнопок "Назад"
    this.elements.backButtons.forEach(button => {
      DOMUtils.addEventListener(button, 'click', () => {
        this.showMainMenu();
      });
    });
  }
  
  setupInitialState() {
    // Изначально скрываем контейнер секций, показываем главное меню и убираем класс состояния
    DOMUtils.hide(this.elements.sectionsContainer);
    this.elements.sections.forEach(section => {
      DOMUtils.hide(section);
    });
    DOMUtils.show(this.elements.mainMenu);
    DOMUtils.removeClass(this.elements.app, 'app-section-open');
  }
  
  setupAccessibility() {
    // Добавляем ARIA атрибуты динамически для кнопок меню
    this.elements.menuButtons.forEach(button => {
      button.setAttribute('role', 'button');
      
      // Добавляем описания для скрин-ридеров
      const sectionName = button.textContent.trim();
      if (sectionName && !button.hasAttribute('aria-label')) {
        button.setAttribute('aria-label', `Открыть раздел ${sectionName}`);
      }
    });
    
    // Добавляем ARIA атрибуты для кнопок "Назад"
    this.elements.backButtons.forEach(button => {
      button.setAttribute('role', 'button');
      if (!button.hasAttribute('aria-label')) {
        button.setAttribute('aria-label', 'Вернуться к главному меню');
      }
    });
  }
  
  showMainMenu() {
    // Обновляем состояние
    this.stateManager.updateState({
      currentSection: null,
      isSectionOpen: false
    });
    
    // Убираем класс состояния приложения - это скроет меню и секции через CSS
    DOMUtils.removeClass(this.elements.app, 'app-section-open');
    
    // Показываем главное меню (оно будет видимым, когда у .app нет класса app-section-open)
    DOMUtils.show(this.elements.mainMenu);
    
    // Скрываем все секции
    this.elements.sections.forEach(section => {
      DOMUtils.hide(section);
    });
    
    // Скрываем контейнер секций
    DOMUtils.hide(this.elements.sectionsContainer);
    
    // Выполняем тактильную отдачу
    if (this.telegramModule) {
      this.telegramModule.hapticFeedback('light');
    }
    
    // Уведомляем другие модули о возврате к главному меню
    this.eventSystem.emit('section:back', {});
 }
 
  showSection(sectionKey) {
    // Проверяем, существует ли такой раздел
    if (!appConfig.navigation.sections.includes(sectionKey)) {
      console.warn(`Раздел ${sectionKey} не найден`);
      return;
    }
    
    // Добавляем класс для состояния приложения - это скроет меню и покажет секции через CSS
    DOMUtils.addClass(this.elements.app, 'app-section-open');
    
    // Обновляем состояние
    this.stateManager.updateState({
      currentSection: sectionKey,
      isSectionOpen: true
    });
    
    // Скрываем главное меню (оно будет скрыто, когда у .app есть класс app-section-open)
    DOMUtils.hide(this.elements.mainMenu);
    
    // Скрываем все секции
    this.elements.sections.forEach(section => {
      DOMUtils.hide(section);
    });
    
    // Показываем выбранную секцию
    const targetSection = DOMUtils.getElement(`section-${sectionKey}`);
    if (targetSection) {
      DOMUtils.show(targetSection);
    }
    
    // Показываем контейнер секций
    DOMUtils.show(this.elements.sectionsContainer);
    
    // Выполняем тактильную отдачу
    if (this.telegramModule) {
      this.telegramModule.hapticFeedback('light');
    }
    
    // Уведомляем другие модули о смене раздела
    this.eventSystem.emit('section:change', { section: sectionKey });
  }
 
   // Проверка, инициализирован ли модуль
 isInitialized() {
    return this.isInitialized;
  }
}

export default NavigationModule;