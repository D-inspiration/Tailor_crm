// Tailor CRM - Main Application JavaScript

// IndexedDB for offline data storage
const DB_NAME = 'TailorCRM';
const DB_VERSION = 1;

class OfflineStore {
  constructor() {
    this.db = null;
    this.init();
  }

  async init() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => {
        this.db = request.result;
        resolve(this.db);
      };

      request.onupgradeneeded = (event) => {
        const db = event.target.result;

        // Customers store
        if (!db.objectStoreNames.contains('customers')) {
          const customerStore = db.createObjectStore('customers', { keyPath: 'id', autoIncrement: true });
          customerStore.createIndex('name', 'name', { unique: false });
          customerStore.createIndex('phone', 'phone', { unique: true });
        }

        // Orders store
        if (!db.objectStoreNames.contains('orders')) {
          const orderStore = db.createObjectStore('orders', { keyPath: 'id', autoIncrement: true });
          orderStore.createIndex('customer_id', 'customer_id', { unique: false });
          orderStore.createIndex('status', 'status', { unique: false });
        }

        // Sync queue for pending changes
        if (!db.objectStoreNames.contains('syncQueue')) {
          db.createObjectStore('syncQueue', { keyPath: 'id', autoIncrement: true });
        }
      };
    });
  }

  // Save customer offline
  async saveCustomer(customer) {
    await this.init();
    return new Promise((resolve, reject) => {
      const tx = this.db.transaction('customers', 'readwrite');
      const store = tx.objectStore('customers');
      const request = store.put(customer);
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  // Get all customers from offline store
  async getCustomers() {
    await this.init();
    return new Promise((resolve, reject) => {
      const tx = this.db.transaction('customers', 'readonly');
      const store = tx.objectStore('customers');
      const request = store.getAll();
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  // Queue action for when back online
  async queueAction(action) {
    await this.init();
    return new Promise((resolve, reject) => {
      const tx = this.db.transaction('syncQueue', 'readwrite');
      const store = tx.objectStore('syncQueue');
      const request = store.add({
        action: action,
        timestamp: new Date().toISOString(),
        synced: false
      });
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  // Get pending sync actions
  async getPendingActions() {
    await this.init();
    return new Promise((resolve, reject) => {
      const tx = this.db.transaction('syncQueue', 'readonly');
      const store = tx.objectStore('syncQueue');
      const request = store.getAll();
      request.onsuccess = () => {
        const actions = request.result.filter(a => !a.synced);
        resolve(actions);
      };
      request.onerror = () => reject(request.error);
    });
  }
}

// Initialize offline store
const store = new OfflineStore();

// Register service worker
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/static/js/sw.js')
      .then((registration) => {
        console.log('SW registered:', registration.scope);
      })
      .catch((error) => {
        console.log('SW registration failed:', error);
      });
  });
}

// Online/offline detection
function updateOnlineStatus() {
  const banner = document.querySelector('.offline-banner');
  if (banner) {
    if (navigator.onLine) {
      banner.classList.remove('show');
      // Try to sync pending actions
      syncPendingActions();
    } else {
      banner.classList.add('show');
    }
  }
}

window.addEventListener('online', updateOnlineStatus);
window.addEventListener('offline', updateOnlineStatus);

// Sync pending actions when back online
async function syncPendingActions() {
  try {
    const actions = await store.getPendingActions();
    for (const action of actions) {
      // Attempt to sync with server
      console.log('Syncing action:', action);
      // Mark as synced
      action.synced = true;
    }
  } catch (error) {
    console.error('Sync failed:', error);
  }
}

// Voice input helper (for future feature)
function setupVoiceInput(inputElement) {
  if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      inputElement.value = transcript;
      inputElement.dispatchEvent(new Event('input'));
    };

    return recognition;
  }
  return null;
}

// Export for use in other scripts
window.TailorCRM = {
  store,
  syncPendingActions,
  setupVoiceInput
};
