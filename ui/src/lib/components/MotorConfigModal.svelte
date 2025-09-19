<script lang="ts">
  import { getIRLRuntimeParams, updateIRLRuntimeParams } from '$lib/api-client';
  import Modal from './Modal.svelte';
  import MotorConfigForm from './MotorConfigForm.svelte';
  import { Loader } from 'lucide-svelte';

  interface Props {
    isOpen: boolean;
    onClose: () => void;
  }

  let { isOpen, onClose }: Props = $props();

  let runtimeParams = $state<any>(null);
  let isLoadingParams = $state(false);
  let isSavingParams = $state(false);

  async function loadParams() {
    isLoadingParams = true;
    try {
      runtimeParams = await getIRLRuntimeParams();
    } catch (error) {
      console.error('Failed to load runtime params:', error);
    } finally {
      isLoadingParams = false;
    }
  }

  async function saveMotorConfig() {
    if (!runtimeParams) return;

    isSavingParams = true;
    try {
      await updateIRLRuntimeParams(runtimeParams);
    } catch (error) {
      console.error('Failed to save runtime params:', error);
    } finally {
      isSavingParams = false;
    }
  }

  function handleClose() {
    onClose();
    runtimeParams = null;
  }

  $effect(() => {
    if (isOpen && !runtimeParams && !isLoadingParams) {
      loadParams();
    }
  });
</script>

<Modal isOpen={isOpen} title="Motor Configuration" onClose={handleClose} wide={true}>
  {#if isLoadingParams}
    <div class="flex items-center justify-center py-8">
      <Loader size={24} class="animate-spin text-blue-500" />
      <span class="ml-2 text-gray-600 dark:text-gray-400">Loading motor configuration...</span>
    </div>
  {:else if runtimeParams}
    <MotorConfigForm {runtimeParams} />

    <div class="flex justify-end gap-3 pt-4">
      <button
        onclick={handleClose}
        class="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600 border border-gray-300 dark:border-gray-600"
      >
        Cancel
      </button>
      <button
        onclick={saveMotorConfig}
        disabled={isSavingParams}
        class="px-4 py-2 bg-blue-500 hover:bg-blue-600 disabled:bg-blue-300 text-white border border-blue-600 flex items-center gap-2"
      >
        {#if isSavingParams}
          <Loader size={16} class="animate-spin" />
        {/if}
        Save Changes
      </button>
    </div>
  {:else}
    <div class="text-center py-8 text-gray-600 dark:text-gray-400">
      Failed to load motor configuration
    </div>
  {/if}
</Modal>