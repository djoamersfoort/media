import { Api } from "../__generated__/api"
import { jwtDecode } from 'jwt-decode'

const OAUTH_SERVER = import.meta.env.VITE_OAUTH_SERVER
const CLIENT_ID = import.meta.env.VITE_CLIENT_ID
const API_BASE = import.meta.env.VITE_API_BASE
const REDIRECT_URL = import.meta.env.VITE_REDIRECT_URL
const SCOPES = ['openid', 'user/basic', 'media']

function base64url(arrayBuffer: ArrayBuffer) {
    return btoa(String.fromCharCode(...new Uint8Array(arrayBuffer)))
        .replace(/\+/g, '-')
        .replace(/\//g, '_')
        .replace(/=+$/, '');
}

async function generatePkce() {
    const verifier = Array.from(crypto.getRandomValues(new Uint8Array(32)))
        .map(b => b.toString(16).padStart(2, '0'))
        .join('');

    const encoder = new TextEncoder();
    const data = encoder.encode(verifier);
    const hash = await crypto.subtle.digest('SHA-256', data);
    const challenge = base64url(hash);

    return { verifier, challenge };
}

const urlParams = new URLSearchParams(window.location.search)
if (urlParams.has('code') && urlParams.get('state') === localStorage.getItem('state')) {
    const code = urlParams.get('code')
    const verifier = localStorage.getItem('code_verifier')
    localStorage.removeItem('code_verifier')
    const res = await fetch(`${OAUTH_SERVER}/token/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({
            grant_type: 'authorization_code',
            code: code || '',
            redirect_uri: REDIRECT_URL,
            client_id: CLIENT_ID,
            code_verifier: verifier || ''
        }).toString(),
    })
    if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.error_description || errorData.error || `HTTP error! status: ${res.status}`);
    }
    const { id_token } = await res.json()
    localStorage.setItem('token', id_token)

    window.history.replaceState({}, document.title, '/')
}

const token = localStorage.getItem('token')
let decoded = null
try {
    decoded = token ? jwtDecode<{ exp: number }>(token) : null
} catch (e) {
    console.error('Failed to decode token:', e)
}

if (!token || (decoded?.exp||0) * 1000 < Date.now()) {
    const state = crypto.randomUUID()
    const { verifier, challenge } = await generatePkce()
    localStorage.setItem('state', state)
    localStorage.setItem('code_verifier', verifier)
    window.location.href = `${OAUTH_SERVER}/authorize?response_type=code&client_id=${CLIENT_ID}&redirect_uri=${REDIRECT_URL}&scope=${SCOPES.join(' ')}&state=${state}&code_challenge=${challenge}&code_challenge_method=S256`
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
