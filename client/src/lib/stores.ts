import { writable, readable } from 'svelte/store'
import type { Item } from '$lib/types'
import Api from "$lib/api"
import type { User } from '$lib/types'

export const current = writable<Item | null>(null)
export const selected = writable<Item[]>([])
export const user = Api.users.getUser().then(({ data }) => data)
