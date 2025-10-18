/**
 * SferaTC Mini App - Оптимизированная версия
 * Убрана кастомная кнопка "Закрыть", используется нативная от Telegram
 */

class SferaTCMiniApp {
  constructor() {
    this.webApp = null;
    this.isInitialized = false;
    this.currentSection = null;
    
    this.init();
  }

  async init() {
    try {
      // Ждем полной готовности DOM
      if (document.readyState === 'loading') {
        await new Promise(resolve => {
          document.addEventListener('DOMContentLoaded', resolve, { once: true });
        });
      }

      this.setupElements();
      await this.initializeTelegramWebApp();
      this.setupEventListeners();
      this.setupAccessibility();
      
      this.isInitialized = true;
      console.log('✅ SferaTC Mini App инициализировано');
      
    } catch (error) {
      console.error('❌ Ошибка инициализации SferaTC Mini App:', error);
    }
  }

  setupElements() {
    // Кешируем элементы для производительности
    this.elements = {
      mainMenu: document.getElementById('main-menu'),
      sectionsWrapper: document.getElementById('sections'),
      sections: new Map([
        ['screener', document.getElementById('section-screener')],
        ['news', document.getElementById('section-news')],
        ['analyst', document.getElementById('section-analyst')],
        ['game', document.getElementById('section-game')]
      ]),
      buttons: new Map([
        ['screener', document.getElementById('btn-screener')],
        ['news', document.getElementById('btn-news')],
        ['analyst', document.getElementById('btn-analyst')],
        ['game', document.getElementById('btn-game')]
      ]),
      backButtons: document.querySelectorAll('.back-btn')
    };

    // Валидация элементов
    Object.entries(this.elements).forEach(([key, element]) => {
      if (!element && key !== 'backButtons') {
        console.warn(`⚠️ Элемент ${key} не найден`);
      }
    });
  }

  async initializeTelegramWebApp() {
    // Безопасное получение WebApp API
    this.webApp = this.getTelegramWebApp();
    
    if (this.webApp) {
      // Устанавливаем атрибут окружения
      document.body.setAttribute('data-app-env', 'telegram');
      
      // Сигнализируем Telegram о готовности приложения
      try {
        this.webApp.ready();
        console.log('📱 Telegram WebApp готов');
      } catch (error) {
        console.warn('⚠️ Не удалось вызвать webApp.ready():', error);
      }

      // Логируем информацию о пользователе (если доступна)
      this.logUserInfo();
      
    } else {
      // Fallback для браузерного режима
      document.body.setAttribute('data-app-env', 'browser');
      console.log('🌐 Режим браузера активирован');
      
      // Ждем события готовности Telegram API
      window.addEventListener('TelegramWebAppReady', () => {
        this.webApp = this.getTelegramWebApp();
        if (this.webApp) {
          this.webApp.ready();
          console.log('📱 Telegram WebApp готов (асинхронно)');
        }
      }, { once: true });
    }
  }

  getTelegramWebApp() {
    // Безопасное получение WebApp API
    try {
      if (window.Telegram?.WebApp) {
        return window.Telegram.WebApp;
      }
      
      if (window.parent !== window && window.parent?.Telegram?.WebApp) {
        return window.parent.Telegram.WebApp;
      }
    } catch (error) {
      console.debug('Не удалось получить Telegram WebApp:', error);
    }
    
    return null;
  }

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

  setupEventListeners() {
    // Обработчики для кнопок навигации
    this.elements.buttons.forEach((button, sectionKey) => {
      if (button) {
        button.addEventListener('click', () => {
          this.navigateToSection(sectionKey);
        });
        
        // Тактильная отдача для поддерживаемых устройств
        this.addHapticFeedback(button);
      }
    });

    // Обработчики для кнопок "Назад"
    this.elements.backButtons.forEach(button => {
      button.addEventListener('click', () => {
        this.showMainMenu();
      });
    });
  }

  setupAccessibility() {
    // Добавляем ARIA атрибуты динамически
    document.querySelectorAll('.menu-btn').forEach(button => {
      button.setAttribute('role', 'button');
      
      // Добавляем описания для скрин-ридеров
      const sectionName = button.textContent.trim();
      if (sectionName && !button.hasAttribute('aria-label')) {
        button.setAttribute('aria-label', `Открыть раздел ${sectionName}`);
      }
    });
  }

  addHapticFeedback(element) {
    if (this.webApp?.HapticFeedback) {
      element.addEventListener('click', () => {
        try {
          this.webApp.HapticFeedback.impactOccurred('light');
        } catch (error) {
          console.debug('Тактильная отдача не поддерживается:', error);
        }
      });
    }
  }

  navigateToSection(sectionKey) {
    const section = this.elements.sections.get(sectionKey);
    
    if (!section) {
      console.warn(`Раздел ${sectionKey} не найден`);
      return;
    }

    // Скрываем главное меню
    this.elements.mainMenu?.classList.add('hidden');
    this.elements.sectionsWrapper?.classList.add('visible');
    
    // Показываем выбранный раздел
    section.classList.add('active');
    this.currentSection = sectionKey;
    
    console.log(`🔄 Переход к разделу: ${sectionKey}`);
  }

  showMainMenu() {
    // Скрываем все активные разделы
    this.elements.sections.forEach(section => {
      section.classList.remove('active');
    });

    // Показываем главное меню
    this.elements.mainMenu?.classList.remove('hidden');
    this.elements.sectionsWrapper?.classList.remove('visible');
    
    this.currentSection = null;
    console.log('🏠 Возврат к главному меню');
  }

  // Публичный API для внешнего использования
  getCurrentSection() {
    return this.currentSection;
  }

  isTelegramEnvironment() {
    return document.body.getAttribute('data-app-env') === 'telegram';
  }
}

// Инициализация приложения
const app = new SferaTCMiniApp();

// Экспорт для возможного использования в других скриптах
window.SferaTCApp = app;
