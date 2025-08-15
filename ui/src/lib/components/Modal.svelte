<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { X } from 'lucide-svelte';

  const dispatch = createEventDispatcher();

  export let open = false;
  export let title = '';
  export let showCloseButton = true;

  function closeModal() {
    open = false;
    dispatch('close');
  }

  function handleBackdropClick(event: MouseEvent) {
    if (event.target === event.currentTarget) {
      closeModal();
    }
  }

  function handleBackdropKeydown(event: KeyboardEvent) {
    if (event.key === 'Enter' || event.key === ' ') {
      closeModal();
    }
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Escape' && open) {
      closeModal();
    }
  }
</script>

<svelte:window on:keydown={handleKeydown} />

{#if open}
  <div
    class="fixed inset-0 z-50 flex items-center justify-center"
    role="dialog"
    aria-modal="true"
    aria-labelledby={title ? 'modal-title' : undefined}
  >
    <!-- Backdrop -->
    <div
      class="fixed inset-0 bg-black/50 transition-opacity"
      on:click={handleBackdropClick}
      on:keydown={handleBackdropKeydown}
      role="button"
      tabindex="-1"
    ></div>
    
    <!-- Modal -->
    <div class="relative z-10 w-full max-w-md mx-4">
      <div class="bg-surface-50 dark:bg-surface-800 shadow-xl border border-surface-200 dark:border-surface-700">
        <!-- Header -->
        {#if title || showCloseButton}
          <div class="flex items-center justify-between p-4 border-b border-surface-200 dark:border-surface-700">
            {#if title}
              <h2 id="modal-title" class="text-lg font-medium text-foreground-light dark:text-foreground-dark">
                {title}
              </h2>
            {:else}
              <div></div>
            {/if}
            
            {#if showCloseButton}
              <button
                on:click={closeModal}
                class="p-1 text-surface-400 hover:text-surface-600 dark:text-surface-500 dark:hover:text-surface-300 hover:bg-surface-100 dark:hover:bg-surface-700 transition-colors"
                aria-label="Close modal"
              >
                <X size={20} />
              </button>
            {/if}
          </div>
        {/if}
        
        <!-- Content -->
        <div class="p-4">
          <slot />
        </div>
        
        <!-- Footer -->
        <slot name="footer" />
      </div>
    </div>
  </div>
{/if}