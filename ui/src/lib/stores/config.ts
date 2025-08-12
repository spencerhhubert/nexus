import { writable } from 'svelte/store';
import { browser } from '$app/environment';

export interface UserConfig {
  theme: 'light' | 'dark';
}

const DEFAULT_CONFIG: UserConfig = {
  theme: 'light',
};

const CONFIG_KEY = 'user-config';

function createConfigStore() {
  const { subscribe, set, update } = writable<UserConfig>(DEFAULT_CONFIG);

  return {
    subscribe,
    update: (updater: (config: UserConfig) => UserConfig) => {
      update(config => {
        const newConfig = updater(config);
        if (browser) {
          localStorage.setItem(CONFIG_KEY, JSON.stringify(newConfig));
        }
        return newConfig;
      });
    },
    set: (config: UserConfig) => {
      set(config);
      if (browser) {
        localStorage.setItem(CONFIG_KEY, JSON.stringify(config));
      }
    },
    init: () => {
      if (browser) {
        try {
          const stored = localStorage.getItem(CONFIG_KEY);
          if (stored) {
            const config = JSON.parse(stored) as UserConfig;
            set(config);
            return;
          }
        } catch (error) {
          console.warn('Failed to parse stored config:', error);
        }

        // If no stored config or parsing failed, use system preference for theme
        const prefersDark = window.matchMedia(
          '(prefers-color-scheme: dark)'
        ).matches;
        const initialConfig: UserConfig = {
          theme: prefersDark ? 'dark' : 'light',
        };
        set(initialConfig);
        localStorage.setItem(CONFIG_KEY, JSON.stringify(initialConfig));
      }
    },
  };
}

export const config = createConfigStore();

// Apply theme changes to document
if (browser) {
  config.subscribe(value => {
    document.documentElement.classList.toggle('dark', value.theme === 'dark');
  });
}
