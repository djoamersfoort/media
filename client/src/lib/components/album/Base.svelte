<script lang="ts">
    import type { AlbumCreate, AlbumList } from "$lib/types"

    export let album: AlbumCreate | AlbumList
</script>

<div class="album">
    {#if "preview" in album && album.preview}
        <img class="preview" src="{album.preview.cover_path}" alt="">
    {/if}
    <div class="meta">
        <div class="name">{album.name}</div>
        <div class="description">{album.description}</div>
    </div>
</div>

<style>
    .album {
        position: relative;
        aspect-ratio: 1920/1080;
        background: #303039;
    }

    .album .meta {
        position: absolute;
        bottom: 0;
        left: 0;
        right: 0;
        padding: 5px;
        background: #00000030;
    }
    .album .meta .name {
        font-weight: bold;
    }

    .preview {
        position: absolute;
        left: 0;
        top: 0;
        width: 100%;
        height: 100%;
        object-fit: cover;
        object-position: center;
    }
</style>
