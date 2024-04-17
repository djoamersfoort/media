<script lang="ts">
    import Api from "$lib/api";
    import {faPlus} from "@fortawesome/free-solid-svg-icons";
    import {push} from "svelte-spa-router";
    import Menu from "$lib/components/menu/Menu.svelte";
    import { link } from "svelte-spa-router";
    import ModeSwitch from "$lib/components/ModeSwitch.svelte";

    const smoelen = Api.smoelen.getSmoelen()
        .then(({ data }) => data)
</script>

{#await smoelen}
    <p>Loading...</p>
{:then smoelen}
    <Menu name="Smoelen" href="/" />
    <div class="smoelen">
        {#each smoelen as smoel (smoel.id)}
            <a href="/smoelen/{smoel.id}" use:link class="smoel">
                <div class="preview">
                    <div class="background">
                        {#each smoel.items as item (item.id)}
                            <img src="{item.cover_path}" alt="{smoel.name}">
                        {/each}
                    </div>
                    <img src="{smoel.preview.cover_path}" alt="{smoel.name}" class="primary">
                </div>
                <div class="name">{smoel.name}</div>
            </a>
        {/each}
    </div>
{/await}
<ModeSwitch mode="smoelen" />

<style>
    .smoelen {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
        gap: 5px;
        padding: 5px;
    }

    .smoel {
        display: flex;
        flex-direction: column;
        gap: 20px;
        align-items: center;
        padding: 50px;
        text-decoration: none;
        color: #fff;
    }

    .preview {
        position: relative;
        height: 120px;
    }

    img {
        height: 130px;
        aspect-ratio: 80/120;
        object-fit: cover;
        position: absolute;
        left: 50%;
        top: 50%;
        border: 5px solid #303039;
        border-radius: 15px;
    }

    .primary {
        position: absolute;
        translate: -50% -50%;
    }
    .background img {
        height: 100px;
    }

    .background img:last-child {
        translate: calc(-50% + 50px) -50%;
        rotate: 20deg;
    }
    .background img:first-child {
        translate: calc(-50% - 50px) -50%;
        rotate: -20deg
    }
</style>
