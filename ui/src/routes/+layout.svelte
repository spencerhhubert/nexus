<script lang="ts">
  import '../app.css';
  import userSettings from '$lib/stores/user-settings.svelte';
  import { onMount } from 'svelte';
 	import favicon from '$lib/assets/favicon.svg';

  interface Props {
    children: import('svelte').Snippet;
  }

  let { children }: Props = $props();

  onMount(() => {
    // Apply dark class to html element
    const html = document.documentElement;
    if ($userSettings.theme === 'dark') {
      html.classList.add('dark');
    } else {
      html.classList.remove('dark');
    }
  });

  // Watch for theme changes
  $effect(() => {
    const html = document.documentElement;
    if ($userSettings.theme === 'dark') {
      html.classList.add('dark');
    } else {
      html.classList.remove('dark');
    }
  });
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

<main>
  {@render children()}
</main>
