// Система событий для коммуникации между модулями
class EventSystem {
  constructor() {
    this.events = new Map();
 }
  
  subscribe(event, callback) {
    if (!this.events.has(event)) {
      this.events.set(event, []);
    }
    this.events.get(event).push(callback);
  }
  
  unsubscribe(event, callback) {
    if (this.events.has(event)) {
      const index = this.events.get(event).indexOf(callback);
      if (index > -1) {
        this.events.get(event).splice(index, 1);
      }
    }
  }
  
 emit(event, data) {
    if (this.events.has(event)) {
      this.events.get(event).forEach(callback => callback(data));
    }
  }
}

export default EventSystem;