<script lang="ts">
  import type { EncoderStatus } from '$lib/types/websocket';
  import BadgeWithTitle from './BadgeWithTitle.svelte';

  interface Props {
    lifecycleStage: string;
    sortingState: string;
    feederState: string | null;
    encoder: EncoderStatus | null;
  }

  let { lifecycleStage, sortingState, feederState, encoder }: Props = $props();

  function formatSpeed(speedCmPerS: number): string {
    return `${speedCmPerS.toFixed(1)} cm/s`;
  }
</script>

<div class="bg-white dark:bg-gray-800 p-6 border border-gray-200 dark:border-gray-700">
  <h2 class="text-xl font-semibold mb-4 text-gray-900 dark:text-gray-100">System Status</h2>

  <div class="flex gap-6">
    <!-- Left side - System States -->
    <div class="flex-1 space-y-6">
      <BadgeWithTitle title="Lifecycle Stage" text={lifecycleStage} variant="blue" />
      <BadgeWithTitle title="Sorting State" text={sortingState} variant="green" />
      <BadgeWithTitle title="Feeder State" text={feederState || 'Unknown'} variant="yellow" />
    </div>

    <!-- Right side - Conveyor Speed -->
    <div class="flex-1">
      <h3 class="text-sm text-gray-500 dark:text-gray-400 mb-3">Conveyor Speed</h3>
      {#if encoder}
        <div class="grid grid-cols-2 gap-6">
          <BadgeWithTitle title="Current" text={formatSpeed(encoder.current_speed_cm_per_s)} variant="blue" />
          <BadgeWithTitle title="1s Avg" text={formatSpeed(encoder.average_speed_1s_cm_per_s)} variant="yellow" />
          <BadgeWithTitle title="5s Avg" text={formatSpeed(encoder.average_speed_5s_cm_per_s)} variant="purple" />
          <BadgeWithTitle title="History" text="{encoder.position_history_count} points" variant="gray" />
        </div>
      {:else}
        <div class="text-gray-500 dark:text-gray-400 text-sm">
          No encoder data available
        </div>
      {/if}
    </div>
  </div>
</div>