// Управление состоянием приложения
class StateManager {
  constructor() {
    this.state = {
      currentSection: null,
      isSectionOpen: false,
      telegramReady: false,
      webApp: null
    };
    
    this.listeners = new Map();
  }
  
  // Получить текущее состояние
  getState() {
    return { ...this.state };
  }
  
  // Обновить состояние
  updateState(newState) {
    const prevState = { ...this.state };
    this.state = { ...this.state, ...newState };
    
    // Уведомить слушателей об изменении состояния
    this.notifyListeners(prevState, this.state);
  }
  
  // Подписаться на изменения состояния
  subscribe(listener) {
    const id = Symbol('listener');
    this.listeners.set(id, listener);
    return () => this.listeners.delete(id); // Функция для отписки
  }
  
  // Уведомить слушателей об изменении состояния
 notifyListeners(prevState, newState) {
    for (const listener of this.listeners.values()) {
      listener(prevState, newState);
    }
  }
  
  // Получить значение конкретного свойства состояния
 getValue(key) {
    return this.state[key];
  }
  
  // Установить значение конкретного свойства состояния
  setValue(key, value) {
    const newState = { [key]: value };
    this.updateState(newState);
 }
}

export default StateManager;