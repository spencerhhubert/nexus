<script lang="ts">
	import favicon from '$lib/assets/favicon.svg';
	import '../app.css';
	import SettingsModal from '$lib/components/SettingsModal.svelte';
	import { Settings } from 'lucide-svelte';
	import { config } from '$lib/stores/config';
	import { onMount } from 'svelte';

	let { children } = $props();
	let showSettings = $state(false);

	onMount(() => {
		config.init();
	});

	function openSettings() {
		showSettings = true;
	}
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

<div class="min-h-screen bg-background-light dark:bg-background-dark transition-colors duration-200">
	<!-- Header with settings -->
	<header class="relative w-full p-4">
		<button
			onclick={openSettings}
			class="absolute top-4 right-4 p-2 text-surface-600 dark:text-surface-400 hover:text-surface-800 dark:hover:text-surface-200 hover:bg-surface-100 dark:hover:bg-surface-700 transition-colors"
			aria-label="Open settings"
		>
			<Settings size={20} />
		</button>
	</header>

	<!-- Main content -->
	<main class="px-4 pb-4">
		{@render children?.()}
	</main>
</div>

<SettingsModal bind:open={showSettings} />
