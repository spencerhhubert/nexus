<script lang="ts">
  import Tabs from '$lib/components/Tabs.svelte';
  import LabelingTab from '$lib/components/LabelingTab.svelte';
  import ViewingTab from '$lib/components/ViewingTab.svelte';

  let activeTab = $state('labeling');

  const tabs = [
    { id: 'labeling', label: 'Labeling' },
    { id: 'viewing', label: 'Viewing' }
  ];

  function handleTabChange(tabId: string) {
    activeTab = tabId;
  }
</script>

<svelte:head>
  <title>YOLO Labeler</title>
</svelte:head>

<div class="min-h-screen bg-gray-50">
  <div class="container mx-auto px-4 py-8">
    <h1 class="text-3xl font-bold text-gray-900 mb-8">YOLO Labeler</h1>

    <div class="mb-8">
      <Tabs {tabs} {activeTab} onTabChange={handleTabChange} />
    </div>

    <div>
      {#if activeTab === 'labeling'}
        <LabelingTab />
      {:else if activeTab === 'viewing'}
        <ViewingTab />
      {/if}
    </div>
  </div>
</div>