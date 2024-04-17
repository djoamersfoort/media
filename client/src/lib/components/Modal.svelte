<script lang="ts">
    export let showModal: boolean

    let dialog: HTMLDialogElement

    $: if (dialog && showModal) dialog.showModal()
</script>

<!-- svelte-ignore a11y-click-events-have-key-events a11y-no-noninteractive-element-interactions -->
<dialog
        bind:this={dialog}
        on:close={() => (showModal = false)}
        on:click|self={() => dialog.close()}
>
    <!-- svelte-ignore a11y-no-static-element-interactions -->
    <div on:click|stopPropagation>
        <div class="header">
            <slot name="header" />
        </div>
        <hr />
        <slot />
        <!-- svelte-ignore a11y-autofocus -->
        <button autofocus on:click={() => dialog.close()}>Close</button>
    </div>
</dialog>

<style>
    dialog {
        border-radius: 10px;
        border: none;
        padding: 0;
        background: #303039;
        color: #fff;
        min-width: 400px;
        max-width: 100vw;
    }
    .header {
        text-align: center;
    }
    dialog::backdrop {
        background: rgba(0, 0, 0, 0.3);
    }
    dialog > div {
        padding: 1em;
    }
    dialog[open] {
        animation: zoom 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
    }
    @keyframes zoom {
        from {
            transform: scale(0.95);
        }
        to {
            transform: scale(1);
        }
    }
    dialog[open]::backdrop {
        animation: fade 0.2s ease-out;
    }
    @keyframes fade {
        from {
            opacity: 0;
        }
        to {
            opacity: 1;
        }
    }
    button {
        width: 100%;
        padding: 10px;
        background: #ffffff20;
        border-radius: 5px;
        border: none;
        color: #fff;
        display: block;
        cursor: pointer;
        outline: 0;
    }

    hr {
        border-color: #ffffff10
    }
</style>
