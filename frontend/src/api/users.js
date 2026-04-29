import { http } from './http'

export function getMe(token) {
 return http('/users/me', { token })
}

export function getLeaderboard(token) {
 return http('/users/leaderboard', { token })
}

export function updateProfile(token, data) {
 return http('/users/me', { method: 'PATCH', body: data, token })
}

export function getStoredViewMode() {
 return localStorage.getItem('teamup:view-mode') || 'default'
}

export function setStoredViewMode(mode) {
 if (mode === 'default') {
  localStorage.removeItem('teamup:view-mode')
  return
 }
 localStorage.setItem('teamup:view-mode', mode)
}

export function getMyStats(token) {
 return http('/users/me/stats', { token })
}

export function getMyGames(token) {
 return http('/users/me/games', { token })
}

export function getMyNotifications(token) {
 return http('/users/me/notifications', { token })
}

export function markNotificationRead(token, notificationId) {
 return http(`/users/me/notifications/${notificationId}/read`, { method: 'POST', token })
}

export function markAllNotificationsRead(token) {
 return http('/users/me/notifications/read-all', { method: 'POST', token })
}
