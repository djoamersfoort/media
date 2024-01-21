<script lang="ts">
    import type { IconDefinition } from "@fortawesome/free-solid-svg-icons"
    import Fa from "svelte-fa"
    import { createEventDispatcher } from "svelte"

    const dispatch = createEventDispatcher()

    export let icon: IconDefinition
</script>

<div on:click={() => dispatch('use')} class="action">
    <Fa icon="{icon}" />
</div>

<style>
    .action {
        display: flex;
        justify-content: center;
        align-items: center;
        border-radius: 3px;
        width: 25px;
        cursor: pointer;
    }
</style>
