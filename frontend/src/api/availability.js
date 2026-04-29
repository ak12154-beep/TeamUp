import { http, withQuery } from './http'

export function getVenueSlots(venueId, from, to) {
 return http(withQuery(`/venues/${venueId}/slots`, { from, to }))
}

export function createSlot(token, venueId, data) {
 return http(`/partner/venues/${venueId}/slots`, { method: 'POST', body: data, token })
}

export function updateSlot(token, slotId, data) {
 return http(`/partner/slots/${slotId}`, { method: 'PATCH', body: data, token })
}

export function deleteSlot(token, slotId) {
 return http(`/partner/slots/${slotId}`, { method: 'DELETE', token })
}
