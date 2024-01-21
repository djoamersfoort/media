<script lang="ts">
    import Menu from "$lib/components/menu/Menu.svelte"
    import Action from "$lib/components/menu/Action.svelte"

    import Api from "$lib/api"
    import Masonry from "$lib/components/masonry/Masonry.svelte"
    import FullItem from "$lib/components/FullItem.svelte"
    import { current, selected, user } from '$lib/stores'
    import Fa from "svelte-fa"
    import {
        faArrowLeft,
        faArrowRight,
        faClose,
        faUpload,
        faPencilAlt,
        faTrashCan,
        faStar as faStarSolid
    } from '@fortawesome/free-solid-svg-icons'
    import { faStar } from '@fortawesome/free-regular-svg-icons'
    import Progress from "$lib/components/Progress.svelte"

    import { push } from 'svelte-spa-router'

    export let params: { album: string }

    let album = Api.albums.getAlbum(params.album)
        .then(({ data }) => data)

    let uploading = false
    let status = ''
    let progress = 0

    let selecting = false
    selected.subscribe(selected => {
        selecting = selected.length > 0
    })

    async function deleteCurrent() {
        if ($current === null) return

        await Api.items.deleteItems(params.album, [$current.id])
        current.set(null)
        album = Api.albums.getAlbum(params.album)
            .then(({ data }) => data)
    }
    async function deleteBulk() {
        await Api.items.deleteItems(params.album, $selected.map(item => item.id))
        selected.set([])
        album = Api.albums.getAlbum(params.album)
            .then(({ data }) => data)
    }
    async function setPreview() {
        if ($current === null) return

        await Api.albums.setPreview(params.album, { item_id: $current.id })
        album = Api.albums.getAlbum(params.album)
            .then(({ data }) => data)
    }
    async function previous() {
        if ($current === null) return

        const { items } = await album
        const index = items.indexOf($current)

        let newIndex = index - 1
        if (newIndex < 0) newIndex = items.length - 1

        current.set(items[newIndex])
    }
    async function next() {
        if ($current === null) return

        const { items } = await album
        const index = items.indexOf($current)

        let newIndex = index + 1
        if (newIndex >= items.length) newIndex = 0

        current.set(items[newIndex])
    }
    async function upload() {
        const input = document.createElement('input')
        input.type = 'file'
        input.multiple = true
        input.click()

        input.addEventListener('change', async () => {
            if (!input.files) return

            progress = 0
            uploading = true
            status = 'uploading'

            const files = Array.from(input.files)
            const formData = new FormData()
            files.forEach(file => formData.append('items', file))

            // upload via xhr to see progress
            const xhr = new XMLHttpRequest()
            xhr.open('POST', `${Api.baseUrl}/items/${params.album}`)
            xhr.setRequestHeader('Authorization', `Bearer ${localStorage.getItem('token')}`)
            xhr.upload.addEventListener('progress', ({ loaded, total }) => {
                progress = loaded / total
            })
            xhr.upload.addEventListener('loadend', () => {
                status = 'processing'
            })
            xhr.addEventListener('loadend', () => {
                uploading = false
                progress = 0

                album = Api.albums.getAlbum(params.album)
                    .then(({ data }) => data)
            })
            xhr.send(formData)
        })
    }

    document.body.addEventListener('keyup', ({ key }) => {
        if (key === 'Escape') close()
        if (key === 'ArrowLeft') previous()
        if (key === 'ArrowRight') next()
    })

    async function close() {
        current.set(null)
    }
</script>

{#await album}
    <p>Loading...</p>
{:then album}
    {#if $current}
        <div class="limit-height">
            <Menu name="{new Date($current.date).toLocaleDateString('en-us', {
                year: 'numeric',
                month: 'long',
                day: 'numeric'
            })}" href="/">
                {#await user}{:then user}
                    {#if user.admin || user.id === $current.user}
                        <Action icon="{faTrashCan}" on:use={deleteCurrent} />
                    {/if}
                    {#if user.admin}
                        <Action icon="{$current.id === (album.preview||{}).id ? faStarSolid : faStar}" on:use={setPreview} />
                    {/if}
                {/await}
                <Action icon="{faArrowLeft}" on:use={previous} />
                <Action icon="{faArrowRight}" on:use={next} />
                <Action icon="{faClose}" on:use={close} />
            </Menu>
            <FullItem item="{$current}" />
        </div>
    {:else}
        <Menu name="{album.name}" href="/">
            {#await user}{:then user}
                {#if user.admin}
                    <Action icon="{faPencilAlt}" on:use={() => push(`/${album.id}/edit`)} />
                {/if}
            {/await}
            <Action icon="{faUpload}" on:use={upload} />
        </Menu>
        <Masonry items="{album.items}" />
        {#if selecting}
            <div class="actions">
                <div class="action dangerous" on:click={deleteBulk}>
                    <Fa icon="{faTrashCan}" />
                    Delete
                </div>
            </div>
        {/if}
    {/if}
    {#if uploading}
        <Progress progress="{progress}" status="{status}" />
    {/if}
{/await}

<style>
    .limit-height {
        display: flex;
        flex-direction: column;
        height: 100vh;
    }

    .actions {
        display: flex;
        justify-content: center;
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        padding: 5px;
        background: #303039;
    }
    .action {
        display: flex;
        gap: 3px;
        font-size: small;
        cursor: pointer;
    }

    .action.dangerous {
        color: salmon;
    }
    .action.disabled {
        color: gray;
    }
</style>
