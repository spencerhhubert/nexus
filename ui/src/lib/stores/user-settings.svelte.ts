import { writable, get } from 'svelte/store';

interface UserSettings {
  theme: 'light' | 'dark';
}

const key = 'userSettings';
const defaultValue: UserSettings = {
  theme: 'light',
};

const initialValue = (() => {
  if (typeof window === 'undefined') return defaultValue;
  const stored = localStorage.getItem(key);
  if (!stored) return defaultValue;
  try {
    return JSON.parse(stored);
  } catch {
    return defaultValue;
  }
})();

const store = writable<UserSettings>(initialValue);

if (typeof window !== 'undefined') {
  store.subscribe(v => localStorage.setItem(key, JSON.stringify(v)));

  window.addEventListener('storage', () => {
    const storedValueStr = localStorage.getItem(key);
    if (storedValueStr == null) return;
    if (storedValueStr === 'undefined') {
      store.set(defaultValue);
      return;
    }
    try {
      const localValue = JSON.parse(storedValueStr);
      if (JSON.stringify(localValue) !== JSON.stringify(get(store))) {
        store.set(localValue);
      }
    } catch {
      // Invalid JSON, ignore
    }
  });
}

export default store;
