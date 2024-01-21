<script lang="ts">
    import Menu from "$lib/components/menu/Menu.svelte"
    import Editor from "$lib/components/album/Editor.svelte"
    import Api from "$lib/api"
    import { push } from "svelte-spa-router"
    import type { AlbumCreate } from "$lib/types"

    const album: AlbumCreate = {
        name: '',
        description: ''
    }

    function create() {
        Api.albums.createAlbum(album)
            .then(({ data }) => {
                push(`/${data.id}`)
            })
    }
</script>

<div class="page">
    <Menu name="Create Album" href="/" />
    <Editor album={album} action="Create" on:submit={create} />
</div>

<style>
    .page {
        display: flex;
        flex-direction: column;
        height: 100vh;
    }
</style>
