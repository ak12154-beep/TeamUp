export const DEMO_TOKEN = '__demo_disabled__'

export function isDemoToken() {
  return false
}

export function resetDemoSession() {
  return { user: null }
}

export function getDemoUser() {
  return null
}

export function getDemoEvents() {
  return []
}

export function getDemoSports() {
  return []
}

export function getDemoWallet() {
  return { balance: 0, transactions: [] }
}

export function getDemoPlayerStats() {
  return { onboarding_score: 0, player_rating: 0, games_played: 0 }
}

export function getDemoVenueSlots() {
  return []
}

export function getDemoVenues() {
  return []
}

export function createDemoEvent(payload = {}) {
  return {
    id: 'demo-disabled',
    title: payload.title || 'Game',
    sport_name: payload.sport_name || 'sport',
    venue_name: payload.venue_name || 'venue',
    venue_city: payload.venue_city || 'Bishkek',
    status: 'active',
  }
}

export function getDemoEvent() {
  return null
}

export function joinDemoEvent(event) {
  return event
}

export function leaveDemoEvent(event) {
  return event
}

export function getDemoProfileGames() {
  return []
}

export function updateDemoProfile(form = {}) {
  return form
}

export function getDemoLeaderboard() {
  return []
}
