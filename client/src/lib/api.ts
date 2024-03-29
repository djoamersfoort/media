import { Api } from "../__generated__/api"
import { jwtDecode } from 'jwt-decode'

const OAUTH_SERVER = import.meta.env.VITE_OAUTH_SERVER
const CLIENT_ID = import.meta.env.VITE_CLIENT_ID
const API_BASE = import.meta.env.VITE_API_BASE
const REDIRECT_URL = import.meta.env.VITE_REDIRECT_URL
const SCOPES = ['openid', 'user/basic', 'media']

const urlParams = new URLSearchParams(window.location.search)
if (urlParams.has('code') && urlParams.get('state') === localStorage.getItem('state')) {
    const code = urlParams.get('code')
    const res = await fetch(`${OAUTH_SERVER}/token/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({
            grant_type: 'authorization_code',
            code: code || '',
            redirect_uri: REDIRECT_URL,
            client_id: CLIENT_ID
        }).toString(),
    })
    const { id_token } = await res.json()
    localStorage.setItem('token', id_token)

    window.history.replaceState({}, document.title, '/')
}

const token = localStorage.getItem('token')
const decoded = token ? jwtDecode<{ exp: number }>(token) : null
if (!token || (decoded?.exp||0) * 1000 < Date.now()) {
    const state = crypto.randomUUID()
    localStorage.setItem('state', state)
    window.location.href = `${OAUTH_SERVER}/authorize?response_type=code&client_id=${CLIENT_ID}&redirect_uri=${REDIRECT_URL}&scope=${SCOPES.join(' ')}&state=${state}`
}

export default new Api({
    baseUrl: API_BASE,
    baseApiParams: {
        credentials: "same-origin",
        headers: {
            authorization: `Bearer ${localStorage.getItem('token')}`
        },
        redirect: "follow",
        referrerPolicy: "no-referrer",
    }
})
