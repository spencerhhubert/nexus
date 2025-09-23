<script lang="ts">
  import { pauseSystem, resumeSystem } from '$lib/api-client';
  import { Play, Pause, Wrench } from 'lucide-svelte';

  interface Props {
    onMotorConfigOpen: () => void;
  }

  let { onMotorConfigOpen }: Props = $props();

  async function handlePause() {
    try {
      await pauseSystem();
    } catch (error) {
      console.error('Failed to pause:', error);
    }
  }

  async function handleResume() {
    try {
      await resumeSystem();
    } catch (error) {
      console.error('Failed to resume:', error);
    }
  }
</script>

<div class="bg-white dark:bg-gray-800 p-6 border border-gray-200 dark:border-gray-700">
  <h2 class="text-xl font-semibold mb-4 text-gray-900 dark:text-gray-100">Controls</h2>
  <div class="flex gap-4">
    <button
      onclick={handlePause}
      class="px-4 py-2 bg-yellow-500 hover:bg-yellow-600 text-white border border-yellow-600 flex items-center gap-2"
    >
      <Pause size={16} />
      Pause System
    </button>
    <button
      onclick={handleResume}
      class="px-4 py-2 bg-green-500 hover:bg-green-600 text-white border border-green-600 flex items-center gap-2"
    >
      <Play size={16} />
      Resume System
    </button>
    <button
      onclick={onMotorConfigOpen}
      class="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white border border-blue-600 flex items-center gap-2"
    >
      <Wrench size={16} />
      Motor Config
    </button>
  </div>
</div>