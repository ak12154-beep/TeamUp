import { http } from './http'

export function sendVerificationCode(data) {
 return http('/auth/send-code', { method: 'POST', body: data })
}

export function register(data) {
 return http('/auth/register', { method: 'POST', body: data })
}

export function login(data) {
 return http('/auth/login', { method: 'POST', body: data })
}

export function logout() {
 return http('/auth/logout', { method: 'POST' })
}
