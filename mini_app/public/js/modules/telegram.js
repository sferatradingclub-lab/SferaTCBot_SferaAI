import Helpers from '../utils/helpers.js';
import appConfig from '../config.js';

// Модуль для работы с Telegram WebApp API
class TelegramModule {
  constructor(stateManager) {
    this.stateManager = stateManager;
    this.webApp = null;
    this.isInitialized = false;
  }
  
  async init() {
    try {
      this.webApp = Helpers.getTelegramWebApp();
      
      if (this.webApp) {
        // Устанавливаем атрибут окружения
        document.body.setAttribute('data-app-env', 'telegram');
        
        // Сигнализируем Telegram о готовности приложения
        this.webApp.ready();
        
        // Устанавливаем тему
        this.setTheme();
        
        // Устанавливаем размеры
        this.setupViewport();
        
        // Сохраняем в состояние
        this.stateManager.setValue('telegramReady', true);
        this.stateManager.setValue('webApp', this.webApp);
        
        console.log('📱 Telegram WebApp инициализирован');
        
        // Логируем информацию о пользователе (если доступна)
        this.logUserInfo();
      } else {
        // Fallback для браузерного режима
        document.body.setAttribute('data-app-env', 'browser');
        console.log('🌐 Режим браузера активирован');
        
        // Ждем события готовности Telegram API
        window.addEventListener('TelegramWebAppReady', () => {
          this.webApp = Helpers.getTelegramWebApp();
          if (this.webApp) {
            this.webApp.ready();
            this.stateManager.setValue('telegramReady', true);
            this.stateManager.setValue('webApp', this.webApp);
            console.log('📱 Telegram WebApp готов (асинхронно)');
          }
        }, { once: true });
      }
      
      this.isInitialized = true;
      return true;
    } catch (error) {
      console.error('❌ Ошибка инициализации Telegram модуля:', error);
      return false;
    }
  }
  
  // Установка темы
 setTheme() {
   if (this.webApp) {
     const theme = this.webApp.themeParams;
     // Не изменяем CSS переменную --bg-color, чтобы не конфликтовать с основным стилем
     // Вместо этого, можно установить цвет фона напрямую, если тема отличается
     if (theme?.bg_color && appConfig.debug) {
       console.log('Тема Telegram:', theme);
     }
   }
 }
  
  // Настройка вьюпорта
  setupViewport() {
    if (this.webApp) {
      // Управление кнопкой закрытия
      if (this.webApp.enableClosingConfirmation) {
        this.webApp.enableClosingConfirmation();
      }
      
      // Установка размеров
      this.webApp.expand();
    }
  }
  
  // Логирование информации о пользователе
  logUserInfo() {
    if (!this.webApp?.initDataUnsafe?.user) return;
    
    const user = this.webApp.initDataUnsafe.user;
    console.log('👤 Пользователь:', {
      id: user.id,
      username: user.username,
      firstName: user.first_name,
      lastName: user.last_name,
      language: user.language_code
    });
  }
  
  // Выполнение тактильной отдачи
  hapticFeedback(type = 'light') {
    if (appConfig.telegram.enableHaptic && this.webApp?.HapticFeedback) {
      try {
        switch(type) {
          case 'light':
            this.webApp.HapticFeedback.impactOccurred('light');
            break;
          case 'medium':
            this.webApp.HapticFeedback.impactOccurred('medium');
            break;
          case 'heavy':
            this.webApp.HapticFeedback.impactOccurred('heavy');
            break;
          case 'success':
            this.webApp.HapticFeedback.notificationOccurred('success');
            break;
          case 'error':
            this.webApp.HapticFeedback.notificationOccurred('error');
            break;
        }
      } catch (error) {
        console.debug('Тактильная отдача не поддерживается:', error);
      }
    }
  }
  
  // Получение текущего объекта WebApp
 getWebApp() {
    return this.webApp;
  }
  
  // Проверка, инициализирован ли модуль
  isInitialized() {
    return this.isInitialized;
 }
}

export default TelegramModule;