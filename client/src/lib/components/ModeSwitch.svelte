<script lang="ts">
    import { link } from "svelte-spa-router";

    export let mode: 'albums' | 'smoelen'
</script>

<div class="mode-switch">
    <a href="/" use:link class="mode" class:selected={mode === 'albums'}>Albums</a>
    <a href="/smoelen" use:link class="mode" class:selected={mode === 'smoelen'}>Smoelen ✨</a>
</div>

<style>
    .mode-switch {
        display: flex;
        position: fixed;
        bottom: 15px;
        left: 50%;
        translate: -50%;
        border-radius: 39px;
        overflow: hidden;
        background: #303039;
    }

    .mode {
        padding: 10px;
        text-decoration: none;
        color: #fff;
    }
    .mode.selected {
        background: #ffffff20;
    }
</style>
