<script lang="ts">
  import { X } from 'lucide-svelte';

  interface Props {
    isOpen: boolean;
    title?: string;
    onClose: () => void;
    wide?: boolean;
  }

  let { isOpen = false, title, onClose, wide = false }: Props = $props();

  function handleBackdropClick(event: MouseEvent) {
    if (event.target === event.currentTarget) {
      onClose();
    }
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Escape') {
      onClose();
    }
  }

  function handleBackdropKeydown(event: KeyboardEvent) {
    if (event.key === 'Enter' || event.key === ' ') {
      onClose();
    }
  }
</script>

<svelte:window on:keydown={handleKeydown} />

{#if isOpen}
  <div
    class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
    onclick={handleBackdropClick}
    onkeydown={handleBackdropKeydown}
    role="dialog"
    aria-modal="true"
    tabindex="0"
  >
    <div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 w-full {wide ? 'max-w-4xl' : 'max-w-md'} mx-4">
      <div class="flex justify-between items-center p-6 border-b border-gray-200 dark:border-gray-700">
        {#if title}
          <h2 class="text-xl font-semibold text-gray-900 dark:text-gray-100">{title}</h2>
        {/if}
        <button
          onclick={onClose}
          class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 p-1"
          aria-label="Close modal"
        >
          <X size={20} />
        </button>
      </div>
      <div class="p-6">
        <slot />
      </div>
    </div>
  </div>
{/if}