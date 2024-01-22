<script lang="ts">
    import type { Item } from "$lib/types"
    import { current } from "$lib/stores"
    import Fa from "svelte-fa"
    import { faCheck } from "@fortawesome/free-solid-svg-icons"
    import { selected } from "$lib/stores"

    export let item: Item
    let selecting = false

    let is_selected = false
    selected.subscribe(selected => {
        selecting = selected.length > 0
        is_selected = selected.includes(item)
    })

    function select() {
        if (is_selected) {
            selected.update(items => items.filter(i => i !== item))
            return
        }

        selected.update(items => [...items, item])
    }

    function interact() {
        if (selecting) select()
        else current.set(item)
    }
</script>

<div class="item" class:selected={is_selected}>
    <div class="selector"  on:click={select}>
        {#if is_selected}
            <Fa icon={faCheck} />
        {/if}
    </div>
    <img src="{item.cover_path}" alt="" loading="lazy" on:click={interact} style:aspect-ratio="{item.width}/{item.height}">
</div>

<style>
    .item {
        position: relative;
        cursor: pointer;
    }
    img {
        width: 100%;
    }

    .selector {
        display: flex;
        justify-content: center;
        align-items: center;

        width: 20px;
        height: 20px;
        border-radius: 50%;
        position: absolute;
        top: 5px;
        right: 5px;
        background: #303039;
    }
    .selected .selector {
        background: mediumpurple;
    }
</style>
