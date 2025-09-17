<script lang="ts">
  import VideoFeed from './VideoFeed.svelte';
</script>

<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
  <VideoFeed camera="main_camera" title="Main Camera" />
  <VideoFeed camera="feeder_camera" title="Feeder Camera" />
</div>