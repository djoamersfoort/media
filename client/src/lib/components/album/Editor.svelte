<script lang="ts">
    import type { AlbumCreate, AlbumList } from "$lib/types"
    import Album from "./Album.svelte"
    import { createEventDispatcher } from "svelte"

    const dispatch = createEventDispatcher()

    export let album: AlbumCreate|AlbumList
    export let action: string
</script>

<div class="editor">
    <div class="album">
        <Album album="{album}" />
    </div>
    <form on:submit|preventDefault={() => dispatch('submit', album)}>
        <div class="input-group">
            <label for="name">Name</label>
            <input type="text" bind:value={album.name} id="name">
        </div>
        <div class="input-group">
            <label for="description">Description</label>
            <input type="text" bind:value={album.description} id="description">
        </div>
        <div class="spacer"></div>
        <button type="submit">{action}</button>
    </form>
</div>

<style>
    .editor {
        flex: 1;
        display: flex;
        gap: 10px;
        justify-content: center;
        align-items: center;
    }

    .album {
        flex: 1;
        max-width: 400px;
    }

    form {
        display: flex;
        flex-direction: column;
        gap: 1rem;
    }

    input, button {
        padding: 5px;
        outline: none;
        border: none;
        background: #303039;
        color: #fff;
        width: 230px;
    }
    input:focus, button {
        box-shadow: #ffffff20 0 0 0 1px;
    }

    .input-group {
        display: flex;
        flex-direction: column;
        gap: 5px;
    }

    .spacer {
        flex: 1;
    }
</style>
