<script lang="ts">
  interface Props {
    cameraFrame: string | null;
  }

  let { cameraFrame }: Props = $props();
</script>

<section class="bg-white border border-gray-200 p-5">
  <h2 class="text-xl font-semibold text-gray-800 mb-5 pb-3 border-b border-gray-100">
    Camera Feed
  </h2>

  <div class="bg-gray-50 min-h-[300px] flex items-center justify-center">
    {#if cameraFrame}
      <img
        src="data:image/jpeg;base64,{cameraFrame}"
        alt="Camera feed"
        class="max-w-full max-h-96"
      />
    {:else}
      <div class="text-gray-500 italic">No camera feed</div>
    {/if}
  </div>
</section>
