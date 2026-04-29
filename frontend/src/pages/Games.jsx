import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { getEvents } from '../api/events'
import { getSports } from '../api/sports'
import { DEFAULT_SPORT_IMAGE, getSportImage } from '../utils/sportMedia'
import { getDemoEvents, getDemoSports, isDemoToken } from '../demo/demoData'

const getSportIcon = (name) => {
 if (!name) return '🎮'
 const n = name.toLowerCase()
 if (n.includes('football') || n.includes('soccer')) return '⚽'
 if (n.includes('basketball')) return '🏀'
 if (n.includes('volleyball')) return '🏐'
 if (n.includes('tennis')) return '🎾'
 return '🎮'
}

const getSportLabel = (name, t) => {
 if (!name) return t('common.game')
 const normalized = name.toLowerCase()
 if (normalized.includes('football') || normalized.includes('soccer')) return t('welcome.football')
 if (normalized.includes('basketball')) return t('welcome.basketball')
 if (normalized.includes('volleyball')) return t('welcome.volleyball')
 if (normalized.includes('tennis')) return t('games.tennis')
 return name
}

export default function Games({ token, effectiveRole }) {
 const [sports, setSports] = useState([])
 const [events, setEvents] = useState([])
 const [filters, setFilters] = useState({ city: '', sport_id: '', search: '' })
 const [activeSport, setActiveSport] = useState('all')
 const { t, i18n } = useTranslation()

 const load = () => {
  const payload = { ...filters, status: 'active' }
  if (payload.from) payload.to = new Date(new Date(payload.from).getTime() + 86400000).toISOString()
  getEvents(payload, token).then(setEvents)
 }

 useEffect(() => {
  if (isDemoToken(token)) {
   setSports(getDemoSports())
   setEvents(getDemoEvents().filter((event) => event.status === 'active'))
   return
  }
  getSports().then(setSports)
  load()
 }, [])

 const filteredEvents = events.filter(event => {
  if (activeSport !== 'all' && event.sport_id !== activeSport) return false
  if (filters.search && !event.title.toLowerCase().includes(filters.search.toLowerCase()) &&
    !event.sport_name.toLowerCase().includes(filters.search.toLowerCase()) &&
    !event.venue_name.toLowerCase().includes(filters.search.toLowerCase())) return false
  return true
 }).sort((a, b) => {
  const aWeight = (a.event_type === 'tournament' ? 2 : 0) + (a.is_featured ? 1 : 0)
  const bWeight = (b.event_type === 'tournament' ? 2 : 0) + (b.is_featured ? 1 : 0)
  if (aWeight !== bWeight) return bWeight - aWeight
  return new Date(a.start_at).getTime() - new Date(b.start_at).getTime()
 })

 const handleCoverError = (event) => {
  if (event.currentTarget.dataset.fallbackApplied === 'true') return
  event.currentTarget.dataset.fallbackApplied = 'true'
  event.currentTarget.src = DEFAULT_SPORT_IMAGE
 }

 const getEventStatusLabel = (event) => {
  if (event.status === 'cancelled') return t('games.cancelled')
  if (event.event_type === 'tournament') {
   return event.registration_is_closed ? t('games.registrationClosed') : t('games.registrationOpen')
  }
  return event.current_players >= event.required_players ? t('games.full') : t('games.open')
 }

 const getEventStatusClassName = (event) => {
  if (event.status === 'cancelled') return 'cancelled'
  if (event.event_type === 'tournament') {
   return event.registration_is_closed ? 'closed' : 'open'
  }
  return event.current_players >= event.required_players ? 'full' : 'open'
 }

 return (
  <div className="games-page">
   <div className="page-header">
    <div>
     <h1>{t('games.title')}</h1>
     <p className="page-subtitle">{t('games.subtitle', { count: filteredEvents.length })}</p>
    </div>
    {effectiveRole === 'player' ? (
     <Link to="/games/create" className="btn-primary glass-btn">{t('games.createGame')}</Link>
    ) : null}
   </div>

   {/* Search */}
   <div className="games-toolbar">
    <div className="search-bar glass-card">
     <span className="search-icon">🔍</span>
     <input
      type="text"
      placeholder={t('games.searchPlaceholder')}
      value={filters.search}
      onChange={(e) => setFilters({ ...filters, search: e.target.value })}
     />
    </div>
   </div>

   {/* Sport Tabs */}
   <div className="sport-tabs">
    <button className={`sport-tab ${activeSport === 'all' ? 'active' : ''}`} onClick={() => setActiveSport('all')}>{t('games.all')}</button>
    {sports.map(sport => (
     <button
      key={sport.id}
      className={`sport-tab ${activeSport === sport.id ? 'active' : ''}`}
      onClick={() => setActiveSport(sport.id)}
     >
      {getSportIcon(sport.name)} {getSportLabel(sport.name, t)}
     </button>
    ))}
   </div>

   {/* Games Grid */}
   <div className="games-grid">
    {filteredEvents.map((event) => (
     <div
      key={event.id}
      className={`game-card glass-card ${event.event_type === 'tournament' ? 'game-card-tournament' : ''} ${event.is_featured ? 'game-card-featured' : ''}`}
     >
      <div className="game-card-image">
       <img
        src={getSportImage(event.sport_name)}
        alt={event.title}
        loading="lazy"
        onError={handleCoverError}
       />
       <span className="game-card-sport">{getSportIcon(event.sport_name)} {getSportLabel(event.sport_name, t)}</span>
       {event.event_type === 'tournament' ? (
        <span className="game-card-type-badge">{t('games.tournamentBadge')}</span>
       ) : null}
       <span className={`game-card-status ${getEventStatusClassName(event)}`}>
        ● {getEventStatusLabel(event)}
       </span>
      </div>
      <div className="game-card-body">
       <div className="game-card-top">
        <div className="game-card-title-block">
         <h3>{event.title || `${getSportLabel(event.sport_name, t)} @ ${event.venue_name || t('common.venue')}`}</h3>
         <p className="game-card-subtitle">
          {getSportLabel(event.sport_name, t)} • {event.venue_name || t('common.venue')}
          {event.event_type === 'tournament' ? ` • ${t('games.teamRegistration')}` : ''}
         </p>
        </div>
        <span className="game-credits">
         {event.event_type === 'tournament'
           ?
            `${event.entry_fee_credits_team} ${t('games.creditsPerTeam')}`
           : `${event.cost_credits_per_player} ${t('games.creditsLabel')}`}
        </span>
       </div>
       <div className="game-card-meta">
        <span className="game-card-detail">📅 {new Date(event.start_at).toLocaleDateString(i18n.language === 'ru' ? 'ru-RU' : 'en-US', { weekday: 'long', day: 'numeric', month: 'short' })} {i18n.language === 'ru' ? 'в' : 'at'} {new Date(event.start_at).toLocaleTimeString(i18n.language === 'ru' ? 'ru-RU' : 'en-US', { hour: '2-digit', minute: '2-digit' })}</span>
        <span className="game-card-detail">📍 {event.venue_address || event.venue_city || 'Bishkek'}</span>
        {event.event_type === 'tournament' ? (
         <>
          <span className="game-card-detail game-card-capacity">🏁 {event.registered_teams_count}/{event.teams_count} {t('games.teamsLabel')}</span>
          <span className="game-card-detail">⏳ {t('games.registrationDeadline')}: {new Date(event.registration_deadline).toLocaleDateString(i18n.language === 'ru' ? 'ru-RU' : 'en-US', { day: 'numeric', month: 'short' })}</span>
         </>
        ) : (
         <span className="game-card-detail game-card-capacity">👥 {event.current_players}/{event.required_players} {t('games.participants')}</span>
        )}
       </div>
       <div className="game-card-progress">
        <div
         className="progress-bar"
         style={{
           width: `${event.event_type === 'tournament'
            ?
             ((event.registered_teams_count / event.teams_count) * 100)
            : ((event.current_players / event.required_players) * 100)}%`
         }}
        ></div>
       </div>
       <div className="game-card-footer">
        <Link
         to={`/games/${event.id}`}
         className={`join-btn glass-btn ${event.event_type === 'tournament' && event.registration_is_closed ? 'disabled' : ''}`}
        >
          {event.event_type === 'tournament'
           ?
            (event.registration_is_closed ? t('games.registrationClosed') : t('games.registerTeam'))
           : (event.current_players >= event.required_players ? t('games.full') : t('games.viewDetails'))}
        </Link>
       </div>
      </div>
     </div>
    ))}
   </div>

   {filteredEvents.length === 0 && (
    <div className="empty-state glass-card">
     <span className="empty-icon">🎮</span>
     <h3>{t('games.noGames')}</h3>
     <p>{t('games.noGamesHint')}</p>
     <Link to="/games/create" className="btn-primary glass-btn">{t('games.createGame')}</Link>
    </div>
   )}
  </div>
 )
}
