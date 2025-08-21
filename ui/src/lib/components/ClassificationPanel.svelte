<script lang="ts">
  import type { Writable } from "svelte/store";
  import type { TrajectoryData, ObservationDataForWeb, BricklinkPartData } from "../types";
  import { robotAPI } from "../api";

  interface Props {
    pageState: Writable<any>;
    selectedTrajectory: TrajectoryData | null;
  }

  let { pageState, selectedTrajectory }: Props = $props();

  let selectedObservations = $derived.by(() => {
    if (!selectedTrajectory) return [];
    const filtered = $pageState.observations.filter((obs: ObservationDataForWeb) =>
      selectedTrajectory.observation_ids.includes(obs.observation_id)
    );
    return filtered;
  });

  let partData = $state<BricklinkPartData | null>(null);
  let isLoadingPart = $state(false);
  let partError = $state<string | null>(null);

  async function fetchPartInfo(kindId: string) {
    isLoadingPart = true;
    partError = null;

    try {
      const result = await robotAPI.getBricklinkPart(kindId);
      if (result) {
        partData = result;
      } else {
        partError = 'Part not found';
        partData = null;
      }
    } catch (error) {
      partError = error instanceof Error ? error.message : 'Unknown error';
      partData = null;
    } finally {
      isLoadingPart = false;
    }
  }

  $effect(() => {
    if (selectedTrajectory?.consensus_classification) {
      fetchPartInfo(selectedTrajectory.consensus_classification);
    } else {
      partData = null;
      partError = null;
    }
  });
</script>

<section class="bg-surface-50 dark:bg-surface-800 border border-surface-200 dark:border-surface-700 p-5">
  <h2 class="text-xl font-semibold text-foreground-light dark:text-foreground-dark mb-5 pb-3 border-b border-surface-200 dark:border-surface-700">
    Classification
  </h2>

  {#if selectedTrajectory}
    <!-- Stock Image Area -->
    <div class="mb-4">
      <div class="w-full h-48 flex items-center justify-center text-sm text-gray-700">
        {#if isLoadingPart}
          <div class="text-center">
            <div class="animate-spin w-6 h-6 border-2 border-gray-600 border-t-transparent rounded-full mx-auto mb-2"></div>
            Loading part info...
          </div>
        {:else if partError}
          <div class="text-center text-red-700">
            Error loading part:<br>{partError}
          </div>
        {:else if partData?.image_url}
          <img
            src={partData.image_url}
            alt={partData.name || 'BrickLink part'}
            class="max-w-full max-h-full object-contain"
          />
        {:else}
          Stock image we will pull<br>based on classification id
        {/if}
      </div>
    </div>

    <!-- Observation Images -->
    <div class="mb-4">
      <div class="text-xs text-surface-600 dark:text-surface-400 mb-2">
        Observations ({selectedObservations.length}):
      </div>
      <div class="flex gap-2 overflow-x-auto pb-2">
        {#if selectedObservations.length > 0}
          {#each selectedObservations as observation (observation.observation_id)}
            <div class="flex-shrink-0 w-16 h-16 bg-blue-300 border border-gray-400 flex items-center justify-center">
              {#if observation.masked_image}
                <img
                  src="data:image/jpeg;base64,{observation.masked_image}"
                  alt="Observation {observation.observation_id.slice(0,8)}"
                  class="w-full h-full object-cover"
                />
              {:else}
                <div class="text-xs text-center">No<br>Img</div>
              {/if}
            </div>
          {/each}
        {:else}
          <div class="text-xs text-surface-500 dark:text-surface-400 italic">
            No observations found for this trajectory
          </div>
        {/if}
      </div>
    </div>

    <!-- Classification Details -->
    <div class="space-y-2 text-sm">
      {#if selectedTrajectory.consensus_classification}
        <div>
          <span class="font-medium text-foreground-light dark:text-foreground-dark">Piece name:</span>
          <span class="text-surface-600 dark:text-surface-400">
            {partData?.name || selectedTrajectory.consensus_classification}
          </span>
        </div>
        <div>
          <span class="font-medium text-foreground-light dark:text-foreground-dark">Part ID:</span>
          <span class="text-surface-600 dark:text-surface-400">{selectedTrajectory.consensus_classification}</span>
        </div>
        {#if partData}
          <div>
            <span class="font-medium text-foreground-light dark:text-foreground-dark">Category ID:</span>
            <span class="text-surface-600 dark:text-surface-400">{partData.category_id}</span>
          </div>
          <div>
            <span class="font-medium text-foreground-light dark:text-foreground-dark">Year:</span>
            <span class="text-surface-600 dark:text-surface-400">{partData.year_released}</span>
          </div>
        {/if}
      {:else}
        <div class="text-surface-500 dark:text-surface-400 italic">No classification yet</div>
      {/if}

      {#if selectedTrajectory.target_bin}
        <div class="mt-3 p-2 bg-red-200 border border-red-400 text-red-800 text-xs rounded">
          Bin coordinates: {JSON.stringify(selectedTrajectory.target_bin)}
        </div>
      {/if}
    </div>
  {:else}
    <div class="text-center text-surface-500 dark:text-surface-400 italic py-16">
      Select a trajectory to view classification details
    </div>
  {/if}
</section>
