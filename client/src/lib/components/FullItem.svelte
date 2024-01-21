<script lang="ts">
    import type { Item } from '$lib/types'

    export let item: Item
</script>

<div class="view">
    {#if item.type === 1}
        <img class="content" src="{item.path}" alt="">
    {:else if item.type === 2}
        <video class="content" src="{item.path}" controls autoplay></video>
    {/if}
</div>

<style>
    .view {
        position: relative;
        flex: 1;
    }

    .content {
        position: absolute;
        width: 100%;
        height: 100%;
        object-fit: contain;
    }
</style>
