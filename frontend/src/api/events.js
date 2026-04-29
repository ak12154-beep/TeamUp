import { http, withQuery } from './http'

export function createEvent(token, data) {
 return http('/events', { method: 'POST', body: data, token })
}

export function getEvents(filters = {}, token) {
 return http(withQuery('/events', filters), { token })
}

export function getEvent(id) {
 return http(`/events/${id}`)
}

export function updateEvent(token, id, data) {
 return http(`/events/${id}`, { method: 'PATCH', body: data, token })
}

export function joinEvent(token, id, data = {}) {
 return http(`/events/${id}/join`, { method: 'POST', body: data, token })
}

export function leaveEvent(token, id) {
 return http(`/events/${id}/leave`, { method: 'POST', token })
}

export function registerTournamentTeam(token, id, data) {
 return http(`/events/${id}/register-team`, { method: 'POST', body: data, token })
}

export function rateEvent(token, id, rating) {
 return http(`/events/${id}/ratings`, { method: 'POST', body: { rating }, token })
}
