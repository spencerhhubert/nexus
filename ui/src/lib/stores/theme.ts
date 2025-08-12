import { writable } from 'svelte/store';
import { browser } from '$app/environment';

type Theme = 'light' | 'dark';

function createThemeStore() {
  const { subscribe, set, update } = writable<Theme>('light');

  return {
    subscribe,
    toggle: () => update(theme => (theme === 'light' ? 'dark' : 'light')),
    set: (theme: Theme) => set(theme),
    init: () => {
      if (browser) {
        const stored = localStorage.getItem('theme') as Theme | null;
        const prefersDark = window.matchMedia(
          '(prefers-color-scheme: dark)'
        ).matches;
        const initialTheme = stored || (prefersDark ? 'dark' : 'light');
        set(initialTheme);
      }
    },
  };
}

export const theme = createThemeStore();

// Apply theme to document
if (browser) {
  theme.subscribe(value => {
    document.documentElement.classList.toggle('dark', value === 'dark');
    localStorage.setItem('theme', value);
  });
}
