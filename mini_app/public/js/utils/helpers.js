// Общие вспомогательные функции
class Helpers {
  // Проверка, является ли приложение запущенным в Telegram
  static isTelegramEnvironment() {
    return window.Telegram?.WebApp || (window.parent !== window && window.parent?.Telegram?.WebApp);
  }
  
  // Получение Telegram WebApp объекта
 static getTelegramWebApp() {
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
  
  // Форматирование данных для отладки
  static formatDebugData(message, data = null) {
    return data ? `[DEBUG] ${message}: ${JSON.stringify(data)}` : `[DEBUG] ${message}`;
  }
  
  // Проверка поддержки функций
 static supportsFeature(feature) {
   // Проверяем, доступен ли CSS.supports
   if (typeof CSS !== 'undefined' && CSS.supports) {
     switch(feature) {
       case 'backdrop-filter':
         return CSS.supports('backdrop-filter', 'blur(1px)');
       case 'conic-gradient':
         return CSS.supports('background', 'conic-gradient(from 0deg, red, blue)');
       case 'dvh':
         return CSS.supports('height', '100dvh');
       default:
         return false;
     }
   }
   // Если CSS.supports недоступен, предполагаем, что функция не поддерживается
   return false;
 }
  
  // Задержка (для асинхронных операций)
  static async delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
  
  // Безопасное выполнение функции с обработкой ошибок
 static safeExecute(fn, ...args) {
    try {
      return fn(...args);
    } catch (error) {
      console.error('Ошибка при выполнении функции:', error);
      return null;
    }
  }
}

export default Helpers;