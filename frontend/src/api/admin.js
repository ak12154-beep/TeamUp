import { http, withQuery } from './http'

export function adminGrantCredits(token, data) {
 return http('/admin/wallet/grant', { method: 'POST', body: data, token })
}

export function adminDebitCredits(token, data) {
 return http('/admin/wallet/debit', { method: 'POST', body: data, token })
}

export function adminRevokeGrant(token, transactionId, reason) {
 return http(`/admin/wallet/grant/${transactionId}/revoke`, {
  method: 'POST',
  body: reason ? { reason } : {},
  token,
 })
}

export function adminGetUsers(token, role) {
 return http(withQuery('/admin/users', { role }), { token })
}

export function adminGetUsersWithBalance(token, role, search) {
 return http(withQuery('/admin/users/with-balance', { role, search }), { token })
}

export function adminGetTransactions(token) {
 return http('/admin/wallet/transactions', { token })
}

export function adminGetPartnerStats(token) {
 return http('/admin/stats/partner', { token })
}

export function adminGetPlayerStats(token, userId) {
 return http(`/admin/stats/player/${userId}`, { token })
}

export function adminCreatePartner(token, data) {
 return http('/admin/partners', { method: 'POST', body: data, token })
}

export function adminSetUserAdminRole(token, userId, isAdmin) {
 return http(`/admin/users/${userId}/admin`, {
  method: 'PATCH',
  body: { is_admin: isAdmin },
  token,
 })
}

export function adminCreateTournament(token, data) {
 return http('/admin/tournaments', { method: 'POST', body: data, token })
}

export function adminGetTournamentRegistrations(token, eventId) {
 return http(`/admin/tournaments/${eventId}/registrations`, { token })
}

export function adminDeleteTournamentRegistration(token, eventId, registrationId) {
 return http(`/admin/tournaments/${eventId}/registrations/${registrationId}`, {
  method: 'DELETE',
  token,
 })
}

export function adminUpdateTournamentRegistration(token, eventId, registrationId, data) {
 return http(`/admin/tournaments/${eventId}/registrations/${registrationId}`, {
  method: 'PATCH',
  body: data,
  token,
 })
}
