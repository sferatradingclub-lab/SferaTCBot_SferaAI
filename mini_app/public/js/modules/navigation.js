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
    // Изначально показываем главное меню
    this.showMainMenu();
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
    
    // Скрываем все секции
    const sections = DOMUtils.getElements('.section');
    sections.forEach(section => {
      DOMUtils.removeClass(section, 'active');
      DOMUtils.hide(section);
    });
    
    // Скрываем контейнер секций
    DOMUtils.hide(this.elements.sectionsContainer);
    DOMUtils.removeClass(this.elements.sectionsContainer, 'active');
    
    // Показываем главное меню
    DOMUtils.show(this.elements.mainMenu);
    DOMUtils.addClass(this.elements.mainMenu, 'active');
    
    // Убираем класс состояния приложения
    DOMUtils.removeClass(this.elements.app, 'app-section-open');
    
    console.log('🏠 Возврат к главному меню');
    
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
    
    // Скрываем главное меню
    DOMUtils.hide(this.elements.mainMenu);
    DOMUtils.removeClass(this.elements.mainMenu, 'active');
    
    // Скрываем все секции
    const sections = DOMUtils.getElements('.section');
    sections.forEach(section => {
      DOMUtils.removeClass(section, 'active');
      DOMUtils.hide(section);
    });
    
    // Показываем выбранную секцию
    const targetSection = DOMUtils.getElement(`section-${sectionKey}`);
    if (targetSection) {
      DOMUtils.show(targetSection);
      setTimeout(() => {
        DOMUtils.addClass(targetSection, 'active');
      }, 10); // Небольшая задержка для срабатывания анимации
    }
    
    // Показываем контейнер секций
    DOMUtils.show(this.elements.sectionsContainer);
    DOMUtils.addClass(this.elements.sectionsContainer, 'active');
    
    // Добавляем класс для состояния приложения
    DOMUtils.addClass(this.elements.app, 'app-section-open');
    
    console.log(`🔄 Переход к разделу: ${sectionKey}`);
    
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