<script lang="ts">
    import './layout.css';
    import favicon from '$lib/assets/favicon.svg';
    import { setConfig, initGlobalConfig } from '$lib/config';


    let { children, data} = $props();

    // Make config available via context and globally
    // svelte-ignore state_referenced_locally
    setConfig(data.config);
    // svelte-ignore state_referenced_locally
    initGlobalConfig(data.config);
</script>

<svelte:head><link rel="icon" href={favicon} /></svelte:head>
{@render children()}
