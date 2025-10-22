import DOMUtils from '../utils/dom.js';
import EventSystem from './eventSystem.js';
import appConfig from '../config.js';

// Модуль управления меню
class MenuModule {
  constructor(stateManager, eventSystem) {
    this.stateManager = stateManager;
    this.eventSystem = eventSystem;
    this.elements = {};
    this.isInitialized = false;
 }
  
  init() {
    try {
      this.setupElements();
      this.setupEventListeners();
      this.setupAccessibility();
      
      this.isInitialized = true;
      console.log('✅ Модуль меню инициализирован');
      return true;
    } catch (error) {
      console.error('❌ Ошибка инициализации модуля меню:', error);
      return false;
    }
  }
  
  setupElements() {
    this.elements = {
      mainMenu: DOMUtils.getElement('main-menu'),
      menuButtons: DOMUtils.getElements('.button--menu'),
      sectionsContainer: DOMUtils.getElement('sections-container'),
      app: DOMUtils.getElement('app')
    };
  }
  
  setupEventListeners() {
    // Обработчики для кнопок навигации
    this.elements.menuButtons.forEach(button => {
      const sectionKey = button.dataset.section;
      if (sectionKey) {
        DOMUtils.addEventListener(button, 'click', () => {
          this.navigateToSection(sectionKey);
        });
      }
    });
  }
  
  setupAccessibility() {
    // Добавляем ARIA атрибуты динамически
    this.elements.menuButtons.forEach(button => {
      button.setAttribute('role', 'button');
      
      // Добавляем описания для скрин-ридеров
      const sectionName = button.textContent.trim();
      if (sectionName && !button.hasAttribute('aria-label')) {
        button.setAttribute('aria-label', `Открыть раздел ${sectionName}`);
      }
    });
  }
  
  navigateToSection(sectionKey) {
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
    
    // Скрываем главное меню
    DOMUtils.hide(this.elements.mainMenu);
    DOMUtils.removeClass(this.elements.mainMenu, 'active');
    
    // Добавляем класс для состояния приложения
    DOMUtils.addClass(this.elements.app, 'app-section-open');
    
    console.log(`🔄 Переход к разделу: ${sectionKey}`);
    
    // Уведомляем другие модули о смене раздела
    this.eventSystem.emit('section:change', { section: sectionKey });
  }
  
  showMainMenu() {
    // Обновляем состояние
    this.stateManager.updateState({
      currentSection: null,
      isSectionOpen: false
    });
    
    // Убираем класс для состояния приложения
    DOMUtils.removeClass(this.elements.app, 'app-section-open');
    
    console.log('🏠 Возврат к главному меню');
    
    // Уведомляем другие модули о возврате к главному меню
    this.eventSystem.emit('section:back', {});
 }
  
  // Проверка, инициализирован ли модуль
 isInitialized() {
    return this.isInitialized;
  }
}

export default MenuModule;