<script lang="ts">
    import AlbumView from "$lib/components/AlbumView.svelte";
    import Api from "$lib/api";

    export let params: { smoel: string }
    let smoel = Api.smoelen.getSmoel(params.smoel)
        .then(({ data }) => data)

    function reload() {
        smoel = Api.smoelen.getSmoel(params.smoel)
            .then(({ data }) => data)
    }
</script>

{#await smoel}
    <p>Loading...</p>
{:then smoel}
    <AlbumView
        name="{smoel.name}"
        id="{smoel.id}"
        items="{smoel.items}"
        preview="{undefined}"
        isAlbum="{false}"
        back="/smoelen"
        on:reload={reload}
    />
{/await}
