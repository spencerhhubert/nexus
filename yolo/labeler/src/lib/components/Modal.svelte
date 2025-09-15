<script lang="ts">
  let {
    isOpen = $bindable(false),
    onClose,
    title,
    children
  }: {
    isOpen?: boolean;
    onClose?: () => void;
    title?: string;
    children?: any;
  } = $props();

  function handleClose() {
    isOpen = false;
    onClose?.();
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Escape') {
      handleClose();
    }
  }

  function handleBackdropClick(event: MouseEvent) {
    if (event.target === event.currentTarget) {
      handleClose();
    }
  }
</script>

<svelte:window onkeydown={handleKeydown} />

{#if isOpen}
  <div
    class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
    onclick={handleBackdropClick}
    onkeydown={handleKeydown}
    role="dialog"
    aria-modal="true"
    tabindex="-1"
  >
    <div class="bg-white rounded-lg shadow-xl max-w-7xl max-h-[95vh] w-full mx-4 flex flex-col">
      {#if title}
        <div class="flex items-center justify-between p-4 border-b">
          <h2 class="text-lg font-semibold">{title}</h2>
          <button
            onclick={handleClose}
            class="text-gray-400 hover:text-gray-600 text-xl font-bold w-8 h-8 flex items-center justify-center"
          >
            ×
          </button>
        </div>
      {/if}

      <div class="flex-1 overflow-auto p-4">
        {@render children?.()}
      </div>
    </div>
  </div>
{/if}