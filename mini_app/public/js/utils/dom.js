// Вспомогательные DOM функции
class DOMUtils {
  // Получение элемента по ID
  static getElement(id) {
    return document.getElementById(id);
  }
  
  // Получение элементов по селектору
  static getElements(selector) {
    return document.querySelectorAll(selector);
  }
  
 // Создание элемента
  static createElement(tag, className = '', text = '') {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text) element.textContent = text;
    return element;
  }
  
  // Добавление класса
  static addClass(element, className) {
    if (element instanceof HTMLElement) {
      element.classList.add(className);
    }
  }
  
  // Удаление класса
  static removeClass(element, className) {
    if (element instanceof HTMLElement) {
      element.classList.remove(className);
    }
  }
  
 // Проверка наличия класса
 static hasClass(element, className) {
    return element instanceof HTMLElement && element.classList.contains(className);
  }
  
 // Переключение класса
  static toggleClass(element, className) {
    if (element instanceof HTMLElement) {
      element.classList.toggle(className);
    }
 }
  
  // Добавление обработчика события
 static addEventListener(element, event, handler) {
    if (element instanceof HTMLElement) {
      element.addEventListener(event, handler);
    }
  }
  
  // Удаление обработчика события
 static removeEventListener(element, event, handler) {
    if (element instanceof HTMLElement) {
      element.removeEventListener(event, handler);
    }
  }
  
  // Показ элемента
  static show(element) {
    if (element instanceof HTMLElement) {
      element.style.display = 'block';
    }
  }
  
  // Скрытие элемента
 static hide(element) {
    if (element instanceof HTMLElement) {
      element.style.display = 'none';
    }
 }
  
  // Проверка видимости элемента
 static isVisible(element) {
    return element instanceof HTMLElement && element.style.display !== 'none';
  }
}

export default DOMUtils;