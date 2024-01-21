<script lang="ts">
    import type { AlbumOrder } from "$lib/types"
    import Api from '$lib/api'
    import Album from '$lib/components/album/Album.svelte'
    import Menu from "$lib/components/menu/Menu.svelte"
    import Action from "$lib/components/menu/Action.svelte"
    import { user } from "$lib/stores"

    import { dndzone } from 'svelte-dnd-action'
    import { faPlus } from "@fortawesome/free-solid-svg-icons"
    import { push } from "svelte-spa-router"

    let albums = Api.albums.getAlbums()
        .then(({ data }) => {
            return data.sort((a, b) => a.order - b.order)
        })

    function handleDnd(event: CustomEvent) {
        albums = event.detail.items
    }

    async function handleDndFinalize(event: CustomEvent) {
        handleDnd(event)

        const current = await albums
        const order: AlbumOrder[] = current.map((album, i) => ({ id: album.id, order: i }))
        await Api.albums.orderAlbums(order)
    }
</script>

{#await albums}
    <p>Loading...</p>
{:then albums}
    <Menu name="DJO Media" href="/">
        {#await user}{:then user}
            {#if user.admin}
                <Action icon="{faPlus}" on:use="{() => push('/create')}" />
            {/if}
        {/await}
    </Menu>
    <div use:dndzone={{
        items: albums,
        dropTargetStyle: { outline: 'none' }
    }} on:consider={handleDnd} on:finalize={handleDndFinalize} class="albums">
        {#each albums as album(album.id)}
            <div>
                <Album {album} />
            </div>
        {/each}
    </div>
{/await}

<style>
    .albums {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
        gap: 5px;
        padding: 5px;
    }
</style>
