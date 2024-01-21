<script lang="ts">
    import type { Item } from '$lib/types'
    import ItemComponent from './Item.svelte'

    export let items: Item[]
    let columns: Item[][] = getColumns(items)

    function getColumns(items: Item[]): Item[][] {
        const total = Math.min(Math.max(Math.floor(window.innerWidth / 300), 1), 4)
        const columns: Item[][] = new Array(total).fill(0).map(() => [])
        const lengths: number[] = new Array(total).fill(0)

        items.forEach(item => {
            // get column with the lowest length
            const index = lengths.indexOf(Math.min(...lengths))
            columns[index].push(item)
            lengths[index] += item.height / item.width
        })

        return columns
    }

    window.addEventListener('resize', () => {
        columns = getColumns(items)
    })
</script>

<div class="columns">
    {#each columns as items}
        <div class="column">
            {#each items as item}
                <ItemComponent {item} />
            {/each}
        </div>
    {/each}
</div>

<style>
    .columns {
        display: flex;
        padding: 5px;
        gap: 5px;
    }
    .column {
        flex: 1;
    }
</style>
