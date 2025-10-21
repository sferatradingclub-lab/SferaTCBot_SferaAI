import StateManager from './modules/state.js';
import EventSystem from './modules/eventSystem.js';
import TelegramModule from './modules/telegram.js';
import MenuModule from './modules/menu.js';
import SectionsModule from './modules/sections.js';
import Helpers from './utils/helpers.js';
import appConfig from './config.js';

class SferaTCMiniApp {
  constructor() {
    this.stateManager = new StateManager();
    this.eventSystem = new EventSystem();
    this.isInitialized = false;
  }
  
  async init() {
    try {
      // Ждем полной готовности DOM
      if (document.readyState === 'loading') {
        await new Promise(resolve => {
          document.addEventListener('DOMContentLoaded', resolve, { once: true });
        });
      }
      
      // Инициализируем модули
      await this.initializeAppModules();
      
      this.isInitialized = true;
      console.log('✅ SferaTC Mini App инициализировано');
      
      // Добавляем класс для стилей после полной загрузки
      document.body.classList.add('app-loaded');
      
    } catch (error) {
      console.error('❌ Ошибка инициализации SferaTC Mini App:', error);
    }
  }
  
  async initializeAppModules() {
    // Инициализируем Telegram модуль (сначала, т.к. он устанавливает окружение)
    this.telegramModule = new TelegramModule(this.stateManager);
    await this.telegramModule.init();
    
    // Инициализируем модули в правильном порядке
    this.menuModule = new MenuModule(this.stateManager, this.eventSystem);
    this.menuModule.init();
    
    this.sectionsModule = new SectionsModule(this.stateManager, this.eventSystem, this.telegramModule, this.menuModule);
    this.sectionsModule.init();
    
    // Подписываемся на изменения состояния для отладки (если включен debug)
    if(appConfig.debug) {
      this.stateManager.subscribe((prevState, newState) => {
        console.log('StateChanged:', { prevState, newState });
      });
    }
  }
  
  // Методы для получения модулей (если нужно извне)
  getMenuModule() {
    return this.menuModule;
  }
  
  getSectionsModule() {
    return this.sectionsModule;
  }
  
  getTelegramModule() {
    return this.telegramModule;
  }
  
  getStateManager() {
    return this.stateManager;
 }
  
  // Проверка, инициализировано ли приложение
  isInitialized() {
    return this.isInitialized;
 }
}

// Инициализация приложения
const app = new SferaTCMiniApp();

// Используем IIFE (Immediately Invoked Function Expression) для использования await
(async () => {
  await app.init();
  
  // Экспорт для возможного использования в других скриптах
  window.SferaTCApp = app;
})();