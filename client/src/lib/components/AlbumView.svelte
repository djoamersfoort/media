<script lang="ts">
    import Menu from "$lib/components/menu/Menu.svelte"
    import Action from "$lib/components/menu/Action.svelte"

    import Api from "$lib/api"
    import Masonry from "$lib/components/masonry/Masonry.svelte"
    import FullItem from "$lib/components/FullItem.svelte"
    import Modal from "$lib/components/Modal.svelte"
    import { current, selected, user } from '$lib/stores'
    import Fa from "svelte-fa"
    import {
        faArrowLeft,
        faArrowRight,
        faClose,
        faUpload,
        faPencilAlt,
        faTrashCan,
        faStar as faStarSolid, faUsers
    } from '@fortawesome/free-solid-svg-icons'
    import { faStar } from '@fortawesome/free-regular-svg-icons'
    import Progress from "$lib/components/Progress.svelte"

    import { push } from 'svelte-spa-router'
    import type {Album, Item} from "../../__generated__/api";
    import {createEventDispatcher} from "svelte";

    const dispatch = createEventDispatcher()

    export let name: string
    export let id: string
    export let items: Item[]
    export let preview: string|undefined
    export let isAlbum: boolean
    export let back: string

    let uploading = false
    let status = ''
    let progress = 0
    let showingPeople = false

    let selecting = false
    selected.subscribe(selected => {
        selecting = selected.length > 0
    })

    async function deleteCurrent() {
        if ($current === null) return

        await Api.items.deleteItems(id, [$current.id])
        current.set(null)
        dispatch('reload')
    }
    async function deleteBulk() {
        await Api.items.deleteItems(id, $selected.map(item => item.id))
        selected.set([])
        dispatch('reload')
    }
    async function setPreview() {
        if ($current === null) return

        await Api.albums.setPreview(id, { item_id: $current.id })
        dispatch('reload')
    }
    async function previous() {
        if ($current === null) return

        const index = items.indexOf($current)

        let newIndex = index - 1
        if (newIndex < 0) newIndex = items.length - 1

        current.set(items[newIndex])
    }
    async function next() {
        if ($current === null) return

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
            xhr.open('POST', `${Api.baseUrl}/items/${id}`)
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

                dispatch('reload')
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

    async function showPeople() {
        showingPeople = !showingPeople
    }

    async function deleteAlbum() {
        if (!confirm(`Are you sure you want to delete the album "${name}"? This action cannot be undone.`)) {
            return
        }
        
        try {
            await Api.albums.deleteAlbum(id)
            push('/')
        } catch (error) {
            console.error('Failed to delete album:', error)
            alert('Failed to delete album. Please try again.')
        }
    }
</script>

{#if $current}
    <div class="limit-height">
        <Menu name="{new Date($current.date).toLocaleDateString('en-us', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        })}" href="{back}">
            {#if isAlbum}
                {#await user}{:then user}
                    {#if user.admin || user.id === $current.user}
                        <Action icon="{faTrashCan}" on:use={deleteCurrent} />
                    {/if}
                    {#if user.admin}
                        <Action icon="{$current.id === preview ? faStarSolid : faStar}" on:use={setPreview} />
                    {/if}
                {/await}
            {/if}
            <Action icon="{faUsers}" on:use={showPeople} />
            <Action icon="{faArrowLeft}" on:use={previous} />
            <Action icon="{faArrowRight}" on:use={next} />
            <Action icon="{faClose}" on:use={close} />
        </Menu>
        <FullItem item="{$current}" />
        <Modal bind:showModal={showingPeople}>
            <h2 slot="header">Smoelen</h2>
            {#if $current.smoelen.length > 0}
                <ul>
                    {#each $current.smoelen as smoel (smoel.id)}
                        <li>{smoel.name}</li>
                    {/each}
                </ul>
            {:else}
                <p>(Nog) geen smoelen gevonden</p>
            {/if}
        </Modal>
    </div>
{:else}
    <Menu name="{name}" href="{back}">
        {#if isAlbum}
            {#await user}{:then user}
                {#if user.admin}
                    <Action icon="{faPencilAlt}" on:use={() => push(`/${id}/edit`)} />
                    <Action icon="{faTrashCan}" on:use={deleteAlbum} />
                {/if}
            {/await}
            <Action icon="{faUpload}" on:use={upload} />
        {/if}
    </Menu>
    <Masonry items="{items}" />
    {#if selecting && isAlbum}
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
