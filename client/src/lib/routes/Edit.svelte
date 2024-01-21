<script lang="ts">
    import Api from "$lib/api"
    import type { Album } from "$lib/types"
    import { push } from 'svelte-spa-router'
    import Editor from "$lib/components/album/Editor.svelte"
    import Menu from "$lib/components/menu/Menu.svelte";

    export let params: { album: string }
    let album = Api.albums.getAlbum(params.album)
        .then(({ data }) => data)

    async function update(event: CustomEvent<Album>) {
        await Api.albums.updateAlbum(params.album, event.detail)
        await push(`/${params.album}`)
    }
</script>

{#await album}
    <div>Loading...</div>
{:then album}
    <div class="page">
        <Menu name="Edit {album.name}" href="/" />
        <Editor album={album} action="Update" on:submit={update} />
    </div>
{/await}

<style>
    .page {
        display: flex;
        flex-direction: column;
        height: 100vh;
    }
</style>
