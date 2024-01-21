<script lang="ts">
    import type { AlbumCreate, AlbumList } from '$lib/types'
    import { link } from 'svelte-spa-router'
    import Base from "./Base.svelte"

    export let album: AlbumCreate|AlbumList
</script>

{#if "id" in album}
    <a href="/{album.id}" use:link>
        <Base {album} />
    </a>
{:else}
    <Base {album} />
{/if}

<style>
    a {
        text-decoration: none;
        color: inherit;
    }
</style>
