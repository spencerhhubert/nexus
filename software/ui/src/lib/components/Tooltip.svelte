<script lang="ts">
  interface Props {
    text: string;
    children: any;
  }

  let { text, children }: Props = $props();
</script>

<div class="tooltip-container">
  {@render children()}
  <div class="tooltip-text" role="tooltip">{text}</div>
</div>

<style>
  .tooltip-container {
    position: relative;
    display: inline-block;
  }

  .tooltip-text {
    visibility: hidden;
    background-color: #1f2937;
    color: white;
    text-align: center;
    padding: 0.5rem;
    border-radius: 0;
    position: absolute;
    z-index: 1000;
    bottom: 125%;
    left: 50%;
    margin-left: -60px;
    width: 120px;
    font-size: 0.75rem;
    opacity: 0;
    transition: opacity 0.3s;
  }

  .tooltip-text::after {
    content: "";
    position: absolute;
    top: 100%;
    left: 50%;
    margin-left: -5px;
    border-width: 5px;
    border-style: solid;
    border-color: #1f2937 transparent transparent transparent;
  }

  .tooltip-container:hover .tooltip-text {
    visibility: visible;
    opacity: 1;
  }

  :global(.dark) .tooltip-text {
    background-color: #f3f4f6;
    color: #1f2937;
  }

  :global(.dark) .tooltip-text::after {
    border-color: #f3f4f6 transparent transparent transparent;
  }
</style>