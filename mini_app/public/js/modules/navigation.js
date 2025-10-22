import DOMUtils from '../utils/dom.js';
import EventSystem from './eventSystem.js';
import appConfig from '../config.js';

// Централизованный модуль навигации
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
      backButtons: DOMUtils.getElements('.button--back')
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
    // Изначально показываем главное меню, убираем класс app-section-open
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
    
    // Убираем класс состояния приложения - это скроет меню через CSS
    DOMUtils.removeClass(this.elements.app, 'app-section-open');
    
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
    
    // Обновляем состояние
    this.stateManager.updateState({
      currentSection: sectionKey,
      isSectionOpen: true
    });
    
    // Добавляем класс для состояния приложения - это скроет меню и покажет секции через CSS
    DOMUtils.addClass(this.elements.app, 'app-section-open');
    
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