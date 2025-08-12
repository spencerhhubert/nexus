<script lang="ts">
  interface Props {
    cameraFrame: string | null;
  }

  let { cameraFrame }: Props = $props();
</script>

<section class="bg-surface-50 dark:bg-surface-800 border border-surface-200 dark:border-surface-700 p-5">
  <h2 class="text-xl font-semibold text-foreground-light dark:text-foreground-dark mb-5 pb-3 border-b border-surface-200 dark:border-surface-700">
    Camera Feed
  </h2>

  <div class="bg-surface-100 dark:bg-surface-900 min-h-[300px] flex items-center justify-center">
    {#if cameraFrame}
      <img
        src="data:image/jpeg;base64,{cameraFrame}"
        alt="Camera feed"
        class="max-w-full max-h-96"
      />
    {:else}
      <div class="text-surface-500 dark:text-surface-400 italic">No camera feed</div>
    {/if}
  </div>
</section>
