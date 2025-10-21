import DOMUtils from '../utils/dom.js';
import EventSystem from './eventSystem.js';
import appConfig from '../config.js';

// Модуль управления секциями
class SectionsModule {
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
      
      // Подписываемся на события смены разделов
      this.eventSystem.subscribe('section:change', (data) => {
        this.handleSectionChange(data.section);
      });
      
      this.eventSystem.subscribe('section:back', () => {
        this.showMainMenu();
      });
      
      this.isInitialized = true;
      console.log('✅ Модуль секций инициализирован');
      return true;
    } catch (error) {
      console.error('❌ Ошибка инициализации модуля секций:', error);
      return false;
    }
  }
  
  setupElements() {
    this.elements = {
      sections: new Map(),
      backButtons: DOMUtils.getElements('.button--back'),
      sectionsContainer: DOMUtils.getElement('sections-container'),
      mainMenu: DOMUtils.getElement('main-menu')
    };
    
    // Инициализируем карту секций
    appConfig.navigation.sections.forEach(sectionKey => {
      const sectionElement = DOMUtils.getElement(`section-${sectionKey}`);
      if (sectionElement) {
        this.elements.sections.set(sectionKey, sectionElement);
      }
    });
  }
  
  setupEventListeners() {
    // Обработчики для кнопок "Назад"
    this.elements.backButtons.forEach(button => {
      DOMUtils.addEventListener(button, 'click', () => {
        this.showMainMenu();
      });
    });
 }
  
  setupInitialState() {
    // Скрываем все секции по умолчанию
    this.elements.sections.forEach(section => {
      DOMUtils.hide(section);
    });
  }
  
  handleSectionChange(sectionKey) {
    // Скрываем все секции
    this.elements.sections.forEach((section, key) => {
      DOMUtils.removeClass(section, 'active');
      DOMUtils.hide(section);
    });
    
    // Показываем выбранную секцию
    const targetSection = this.elements.sections.get(sectionKey);
    if (targetSection) {
      DOMUtils.show(targetSection);
      setTimeout(() => {
        DOMUtils.addClass(targetSection, 'active');
      }, 10); // Небольшая задержка для срабатывания анимации
      
      // Выполняем тактильную отдачу
      this.telegramModule.hapticFeedback('light');
    }
  }
  
  showMainMenu() {
    // Скрываем все активные секции
    this.elements.sections.forEach((section, key) => {
      DOMUtils.removeClass(section, 'active');
      setTimeout(() => {
        if(DOMUtils.hasClass(section, 'active')) {
          DOMUtils.hide(section);
        }
      }, appConfig.ui.animationDuration); // Скрываем после завершения анимации
    });
    
    // Выполняем тактильную отдачу
    this.telegramModule.hapticFeedback('light');
  }
  
  // Проверка, инициализирован ли модуль
 isInitialized() {
    return this.isInitialized;
  }
}

export default SectionsModule;