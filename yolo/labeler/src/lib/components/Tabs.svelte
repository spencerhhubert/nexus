<script lang="ts">
  interface Tab {
    id: string;
    label: string;
  }

  interface Props {
    tabs: Tab[];
    activeTab: string;
    onTabChange: (tabId: string) => void;
  }

  let { tabs, activeTab, onTabChange }: Props = $props();
</script>

<div class="border-b border-gray-200">
  <nav class="-mb-px flex space-x-8">
    {#each tabs as tab}
      <button
        onclick={() => onTabChange(tab.id)}
        class="whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm transition-colors {
          activeTab === tab.id
            ? 'border-blue-500 text-blue-600'
            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
        }"
      >
        {tab.label}
      </button>
    {/each}
  </nav>
</div>