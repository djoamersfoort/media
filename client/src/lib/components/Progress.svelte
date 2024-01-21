<script lang="ts">
    export let progress: number
    export let status: string
</script>

<div class="container">
    <div class="progress" style:--progress="{progress}">
        <div class="action">{status}</div>
    </div>
</div>

<style>
    .container {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        display: flex;
        padding: 10px;
        background: #303039;
    }

    .progress {
        position: relative;
        background: #ffffff20;
        flex: 1;
        border-radius: 6px;
        overflow: hidden;
    }
    .action {
        padding: 5px;
        font-size: 10px;
        font-family: monospace;
    }
    .progress::before {
        content: '';
        position: absolute;
        width: calc(var(--progress) * 100%);
        height: 100%;
        background: mediumpurple;
        z-index: -1;
        transition: .3s ease;
    }
</style>
