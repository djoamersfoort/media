import { Api } from "../__generated__/api"
import { jwtDecode } from 'jwt-decode'

const OAUTH_SERVER = "http://localhost:8000/o"
const CLIENT_ID = '9COYxKq9FZVr2WFtFqtkkpM8mdS8Qe23D1ohVNn1'
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
            redirect_uri: 'http://localhost:5173',
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
    window.location.href = `${OAUTH_SERVER}/authorize?response_type=code&client_id=${CLIENT_ID}&redirect_uri=http://localhost:5173&scope=${SCOPES.join(' ')}&state=${state}`
}

export default new Api({
    baseUrl: "http://localhost:7000",
    baseApiParams: {
        credentials: "same-origin",
        headers: {
            authorization: `Bearer ${localStorage.getItem('token')}`
        },
        redirect: "follow",
        referrerPolicy: "no-referrer",
    }
})
