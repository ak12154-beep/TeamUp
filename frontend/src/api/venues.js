import { http } from './http'

export function getVenues() {
 return http('/venues')
}

export function getVenue(id) {
 return http(`/venues/${id}`)
}

export function createVenue(token, data) {
 return http('/partner/venues', { method: 'POST', body: data, token })
}

export function updateVenue(token, id, data) {
 return http(`/partner/venues/${id}`, { method: 'PATCH', body: data, token })
}
