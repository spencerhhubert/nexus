<script lang="ts">
  import { Settings, Wifi, WifiOff, Loader } from 'lucide-svelte';

  interface Props {
    isConnected: boolean;
    isReconnecting: boolean;
    onSettingsOpen: () => void;
  }

  let { isConnected, isReconnecting, onSettingsOpen }: Props = $props();
</script>

<header class="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
  <div class="container mx-auto p-4">
    <div class="flex justify-between items-center">
    <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">Sorting Machine Controls</h1>

    <div class="flex items-center gap-4">
      <!-- Connection Status -->
      <div class="flex items-center gap-2">
        {#if isReconnecting}
          <Loader size={16} class="text-yellow-500 animate-spin" />
          <span class="text-sm text-gray-700 dark:text-gray-300">Reconnecting</span>
        {:else if isConnected}
          <Wifi size={16} class="text-green-500" />
          <span class="text-sm text-gray-700 dark:text-gray-300">Connected</span>
        {:else}
          <WifiOff size={16} class="text-red-500" />
          <span class="text-sm text-gray-700 dark:text-gray-300">Disconnected</span>
        {/if}
      </div>

      <!-- Settings Button -->
      <button
        onclick={onSettingsOpen}
        class="p-2 bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700 border border-gray-300 dark:border-gray-600"
        aria-label="Open settings"
      >
        <Settings size={20} />
      </button>
    </div>
    </div>
  </div>
</header>