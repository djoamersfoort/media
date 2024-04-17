import { wrap } from 'svelte-spa-router/wrap'

import Albums from '$lib/routes/Albums.svelte'
import Create from '$lib/routes/Create.svelte'
import Album from '$lib/routes/Album.svelte'
import Edit from '$lib/routes/Edit.svelte'

import { user } from '$lib/stores'
import Smoelen from "$lib/routes/Smoelen.svelte";
import Smoel from "$lib/routes/Smoel.svelte";

export default {
    '/': Albums,
    '/smoelen': Smoelen,
    '/smoelen/:smoel': Smoel,
    '/create': wrap({
        component: Create,
        conditions: [
            async () => (await user).admin
        ]
    }),
    '/:album': Album,
    '/:album/:edit': wrap({
        component: Edit,
        conditions: [
            async () => (await user).admin
        ]
    }),
}
