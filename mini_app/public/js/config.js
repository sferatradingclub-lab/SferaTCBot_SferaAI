// Конфигурация приложения
const appConfig = {
  // Настройки UI
  ui: {
    animationDuration: 300,
    theme: 'dark',
    breakpoints: {
      mobile: 480,
      tablet: 768,
      desktop: 1024
    }
  },
  
 // Настройки навигации
 navigation: {
    defaultSection: 'screener',
    sections: ['screener', 'news', 'analyst', 'game']
  },
  
  // Настройки Telegram
 telegram: {
    enableHaptic: true,
    enableClosingConfirmation: false
  },
  
 // Режим отладки
  debug: false
};

export default appConfig;