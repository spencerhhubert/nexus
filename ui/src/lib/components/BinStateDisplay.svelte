<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { getBinState, getBricklinkCategoryInfo, getBricklinkCategories, updateBinState } from '$lib/api-client';
  import type { BinStateUpdateMessage, WebSocketMessage } from '$lib/types/websocket';
  import type { components } from '$lib/api-types';
  import { Trash2, Edit, AlertTriangle } from 'lucide-svelte';
  import SearchableDropdown from './SearchableDropdown.svelte';
  import Tooltip from './Tooltip.svelte';

  type BinState = components['schemas']['BinState'];
  type BricklinkCategoryData = components['schemas']['BricklinkCategoryData'];

  let bin_state: BinState | null = $state(null);
  let category_names: Record<string, string> = $state({});
  let websocket: WebSocket | null = null;
  let all_categories: BricklinkCategoryData[] = $state([]);
  let editing_bin: string | null = $state(null);
  let hovered_bin: string | null = $state(null);

  const MISC_CATEGORY = 'misc';
  const UNKNOWN_CATEGORY = 'fallback';

  async function loadBinState() {
    try {
      bin_state = await getBinState();
      await loadCategoryNames();
    } catch (error) {
      console.error('Failed to load bin state:', error);
    }
  }

  async function loadCategories() {
    try {
      all_categories = await getBricklinkCategories();
    } catch (error) {
      console.error('Failed to load categories:', error);
    }
  }

  async function loadCategoryNames() {
    if (!bin_state) return;

    const new_category_names: Record<string, string> = {};

    for (const category_id of Object.values(bin_state.bin_contents)) {
      if (category_id && !category_names[category_id] &&
          category_id !== MISC_CATEGORY &&
          category_id !== UNKNOWN_CATEGORY) {
        try {
          const category_info = await getBricklinkCategoryInfo(parseInt(category_id));
          new_category_names[category_id] = category_info.category_name;
        } catch (error) {
          console.error(`Failed to load category ${category_id}:`, error);
          new_category_names[category_id] = category_id;
        }
      }
    }

    category_names = { ...category_names, ...new_category_names };
  }

  function connectWebSocket() {
    websocket = new WebSocket('ws://localhost:8000/ws');

    websocket.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        if (message.type === 'bin_state_update') {
          handleBinStateUpdate(message as BinStateUpdateMessage);
        }
      } catch (error) {
        console.error('Failed to parse websocket message:', error);
      }
    };

    websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    websocket.onclose = () => {
      setTimeout(connectWebSocket, 5000);
    };
  }

  async function handleBinStateUpdate(message: BinStateUpdateMessage) {
    bin_state = {
      bin_contents: message.bin_contents,
      timestamp: message.timestamp
    };
    await loadCategoryNames();
  }

  function getBinDisplayName(category_id: string | null): string {
    if (!category_id) return 'Empty';
    if (category_id === MISC_CATEGORY) return 'Misc';
    if (category_id === UNKNOWN_CATEGORY) return 'Unknown';
    return category_names[category_id] || 'Occupied';
  }

  async function clearBin(module_idx: number, bin_idx: number) {
    try {
      await updateBinState(
        { distribution_module_idx: module_idx, bin_idx: bin_idx },
        null
      );
    } catch (error) {
      console.error('Failed to clear bin:', error);
    }
  }

  function editBin(bin_key: string) {
    editing_bin = bin_key;
  }

  function cancelEdit() {
    editing_bin = null;
  }

  async function selectCategory(item: { id: string; name: string }) {
    if (!editing_bin) return;

    const { module_idx, bin_idx } = parseBinCoordinates(editing_bin);
    try {
      await updateBinState(
        { distribution_module_idx: module_idx, bin_idx: bin_idx },
        item.id
      );
      editing_bin = null;
    } catch (error) {
      console.error('Failed to update bin category:', error);
    }
  }

  function parseBinCoordinates(bin_key: string): { module_idx: number; bin_idx: number } {
    const [module_idx, bin_idx] = bin_key.split('_').map(Number);
    return { module_idx, bin_idx };
  }

  function groupBinsByModule(): Record<number, Array<{ key: string; bin_idx: number; category_id: string | null }>> {
    if (!bin_state) return {};

    const grouped: Record<number, Array<{ key: string; bin_idx: number; category_id: string | null }>> = {};

    for (const [bin_key, category_id] of Object.entries(bin_state.bin_contents)) {
      const { module_idx, bin_idx } = parseBinCoordinates(bin_key);

      if (!grouped[module_idx]) {
        grouped[module_idx] = [];
      }

      grouped[module_idx].push({ key: bin_key, bin_idx, category_id });
    }

    // Sort bins within each module by bin_idx
    for (const module_bins of Object.values(grouped)) {
      module_bins.sort((a, b) => a.bin_idx - b.bin_idx);
    }

    return grouped;
  }

  onMount(() => {
    loadBinState();
    loadCategories();
    connectWebSocket();
  });

  onDestroy(() => {
    if (websocket) {
      websocket.close();
    }
  });

  const grouped_bins = $derived(groupBinsByModule());

  const duplicate_categories = $derived.by(() => {
    if (!bin_state) return new Set<string>();

    const category_counts: Record<string, number> = {};
    for (const category_id of Object.values(bin_state.bin_contents)) {
      if (category_id) {
        category_counts[category_id] = (category_counts[category_id] || 0) + 1;
      }
    }

    return new Set(
      Object.entries(category_counts)
        .filter(([_, count]) => count > 1)
        .map(([category_id, _]) => category_id)
    );
  });

  const category_dropdown_items = $derived.by(() => [
    { id: MISC_CATEGORY, name: 'Misc' },
    { id: UNKNOWN_CATEGORY, name: 'Unknown' },
    ...all_categories.map(cat => ({ id: cat.category_id.toString(), name: cat.category_name }))
  ]);
</script>

<div class="bin-state-display">
  <h3 class="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100">Bin State</h3>

  {#if bin_state}
    <div class="modules-container">
      {#each Object.entries(grouped_bins).sort(([a], [b]) => Number(a) - Number(b)) as [module_idx, bins]}
        <div class="module-container">
          <h4 class="text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">
            Module {Number(module_idx) + 1}
          </h4>
          <div class="bins-grid">
            {#each bins as { key, bin_idx, category_id }}
              <div
                   role="button"
                   tabindex="0"
                   class="bin-cell"
                   onkeydown={(e) => (e.key === 'Enter' || e.key === ' ') && e.preventDefault()}
                   class:empty={!category_id}
                   class:misc={category_id === MISC_CATEGORY}
                   class:unknown={category_id === UNKNOWN_CATEGORY}
                   class:occupied={category_id && category_id !== MISC_CATEGORY && category_id !== UNKNOWN_CATEGORY}
                   onmouseenter={() => hovered_bin = key}
                   onmouseleave={() => hovered_bin = null}>
                <div class="bin-coordinates">{Number(module_idx) + 1},{bin_idx + 1}</div>
                <div class="bin-content">{getBinDisplayName(category_id)}</div>

                {#if category_id && duplicate_categories.has(category_id)}
                  <div class="warning-icon">
                    <Tooltip text="Multiple bins have the same category">
                      {#snippet children()}
                        <AlertTriangle size={16} color="#f59e0b" />
                      {/snippet}
                    </Tooltip>
                  </div>
                {/if}

                {#if hovered_bin === key}
                  <div class="action-icons">
                    <button class="action-icon trash" onclick={(e) => { e.stopPropagation(); clearBin(Number(module_idx), bin_idx); }} title="Clear bin">
                      <Trash2 size={16} />
                    </button>
                    <button class="action-icon edit" onclick={(e) => { e.stopPropagation(); editBin(key); }} title="Edit category">
                      <Edit size={16} />
                    </button>
                  </div>
                {/if}

                {#if editing_bin === key}
                  <div class="dropdown-overlay">
                    <SearchableDropdown
                      items={category_dropdown_items}
                      onSelect={selectCategory}
                      onClose={cancelEdit}
                      placeholder="Search categories..."
                    />
                  </div>
                {/if}
              </div>
            {/each}
          </div>
        </div>
      {/each}
    </div>
  {:else}
    <div class="text-gray-500 dark:text-gray-400">Loading bin state...</div>
  {/if}
</div>

<style>
  .bin-state-display {
    padding: 1rem;
  }

  .modules-container {
    display: flex;
    gap: 1rem;
    align-items: flex-start;
    width: 100%;
  }

  .module-container {
    border: 1px solid #e5e7eb;
    padding: 1rem;
    background: white;
    flex: 1;
  }

  .bins-grid {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .bin-cell {
    border: 2px solid #d1d5db;
    padding: 0.5rem;
    text-align: center;
    font-size: 0.75rem;
    min-height: 60px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    position: relative;
  }

  .bin-cell.empty {
    border-color: #e5e7eb;
    background-color: #f9fafb;
  }

  .bin-cell.misc {
    border-color: #3b82f6;
    background-color: #dbeafe;
  }

  .bin-cell.unknown {
    border-color: #f59e0b;
    background-color: #fef3c7;
  }

  .bin-cell.occupied {
    border-color: #10b981;
    background-color: #d1fae5;
  }

  .bin-coordinates {
    font-weight: 600;
    color: #374151;
  }

  .bin-content {
    font-size: 0.625rem;
    margin-top: 0.25rem;
    color: #6b7280;
  }

  :global(.dark) .module-container {
    background: #374151;
    border-color: #4b5563;
  }

  :global(.dark) .bin-coordinates {
    color: #f3f4f6;
  }

  :global(.dark) .bin-content {
    color: #d1d5db;
  }

  .warning-icon {
    position: absolute;
    top: 0.25rem;
    right: 0.25rem;
  }

  .action-icons {
    position: absolute;
    top: 0.25rem;
    left: 0.25rem;
    display: flex;
    gap: 0.25rem;
  }

  .action-icon {
    background: rgba(255, 255, 255, 0.9);
    border: 1px solid #d1d5db;
    padding: 0.25rem;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .action-icon:hover {
    background: rgba(255, 255, 255, 1);
  }

  .action-icon.trash:hover {
    background: #fee2e2;
    border-color: #fca5a5;
    color: #dc2626;
  }

  .action-icon.edit:hover {
    background: #dbeafe;
    border-color: #93c5fd;
    color: #2563eb;
  }

  .dropdown-overlay {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    z-index: 1001;
    margin-top: 0.25rem;
  }

  :global(.dark) .action-icon {
    background: rgba(55, 65, 81, 0.9);
    border-color: #4b5563;
    color: #f3f4f6;
  }

  :global(.dark) .action-icon:hover {
    background: rgba(55, 65, 81, 1);
  }

  :global(.dark) .action-icon.trash:hover {
    background: #7f1d1d;
    border-color: #dc2626;
    color: #fca5a5;
  }

  :global(.dark) .action-icon.edit:hover {
    background: #1e3a8a;
    border-color: #2563eb;
    color: #93c5fd;
  }
</style>