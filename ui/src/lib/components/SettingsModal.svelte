<script lang="ts">
  import Modal from './Modal.svelte';
  import { config } from '$lib/stores/config';
  import { Sun, Moon } from 'lucide-svelte';

  export let open = false;

  function closeModal() {
    open = false;
  }

  function toggleTheme() {
    config.update(cfg => ({
      ...cfg,
      theme: cfg.theme === 'light' ? 'dark' : 'light'
    }));
  }
</script>

<Modal bind:open title="Settings" on:close={closeModal}>
  <div class="space-y-4">
    <!-- Theme Toggle -->
    <div class="flex items-center justify-between">
      <div class="flex items-center space-x-2">
        <div class="flex items-center space-x-2 text-surface-600 dark:text-surface-400">
          {#if $config.theme === 'light'}
            <Sun size={18} />
          {:else}
            <Moon size={18} />
          {/if}
          <span class="font-medium">Theme</span>
        </div>
      </div>
      
      <button
        on:click={toggleTheme}
        class="relative inline-flex h-6 w-11 items-center transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:focus:ring-offset-surface-800 {$config.theme === 'dark' ? 'bg-primary-600' : 'bg-surface-200 dark:bg-surface-600'}"
        role="switch"
        aria-checked={$config.theme === 'dark'}
        aria-label="Toggle theme"
      >
        <span
          class="inline-block h-4 w-4 transform bg-white transition-transform {$config.theme === 'dark' ? 'translate-x-6' : 'translate-x-1'}"
        ></span>
      </button>
    </div>
    
    <p class="text-sm text-surface-500 dark:text-surface-400">
      Switch between light and dark mode
    </p>
  </div>
</Modal>