<script lang="ts">
    import { link } from "svelte-spa-router"

    export let name: string
    export let href: string
</script>

<div class="menu">
    <a href="{href}" class="title" use:link>{name}</a>
    <div class="actions">
        <slot />

    </div>
</div>

<style>
    .menu {
        display: flex;
        background: #303039;
        padding: 5px;
        justify-content: space-between;
    }

    .title {
        font-weight: bold;
        color: #fff;
        text-decoration: none;
    }

    .actions {
        display: flex;
    }
</style>
