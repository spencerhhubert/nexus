<script lang="ts">
  import Modal from './Modal.svelte';
  import userSettings from '$lib/stores/user-settings.svelte';
  import { Sun, Moon } from 'lucide-svelte';

  interface Props {
    isOpen: boolean;
    onClose: () => void;
  }

  let { isOpen, onClose }: Props = $props();

  function toggleTheme() {
    userSettings.update(settings => ({
      ...settings,
      theme: settings.theme === 'light' ? 'dark' : 'light'
    }));
  }
</script>

<Modal isOpen={isOpen} title="Settings" onClose={onClose}>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <span class="text-gray-700 dark:text-gray-300">Theme</span>
      <button
        onclick={toggleTheme}
        class="flex items-center gap-2 px-3 py-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 border border-gray-300 dark:border-gray-600"
        aria-label="Toggle theme"
      >
        {#if $userSettings.theme === 'light'}
          <Sun size={16} />
          Light
        {:else}
          <Moon size={16} />
          Dark
        {/if}
      </button>
    </div>
  </div>
</Modal>