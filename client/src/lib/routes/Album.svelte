<script lang="ts">
    import AlbumView from "$lib/components/AlbumView.svelte";
    import Api from "$lib/api";

    export let params: { album: string }
    let album = Api.albums.getAlbum(params.album)
        .then(({ data }) => data)

    function reload() {
        album = Api.albums.getAlbum(params.album)
            .then(({ data }) => data)
    }
</script>

{#await album}
    <p>Loading...</p>
{:then album}
    <AlbumView
        name="{album.name}"
        id="{album.id}"
        items="{album.items}"
        preview="{album.preview?.id}"
        isAlbum="{true}"
        back="/"
        on:reload={reload}
    />
{/await}
