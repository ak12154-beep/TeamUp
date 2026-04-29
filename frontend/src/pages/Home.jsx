import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { adminGetPartnerStats, adminGetTransactions, adminGetUsers } from '../api/admin'
import LanguageSwitcher from '../components/LanguageSwitcher'
import { getEvents } from '../api/events'
import { getMyStats } from '../api/users'
import { getVenues } from '../api/venues'
import { getWalletMe } from '../api/wallet'
import { getDemoEvents, getDemoPlayerStats, getDemoWallet, isDemoToken } from '../demo/demoData'
import { getUserDisplayName } from '../utils/userDisplay'

export default function Home({ user, token, effectiveRole }) {
 const [events, setEvents] = useState([])
 const [balance, setBalance] = useState(0)
 const [venues, setVenues] = useState([])
 const [players, setPlayers] = useState([])
 const [partners, setPartners] = useState([])
 const [transactions, setTransactions] = useState([])
 const [playerStats, setPlayerStats] = useState({
  games_played: 0,
  balance: 0,
  player_rating: 0,
  onboarding_score: null,
  onboarding_level_label: '',
 })
 const [partnerStats, setPartnerStats] = useState(null)
 const { t, i18n } = useTranslation()
 const displayName = getUserDisplayName(user, t('role.partner'))

 useEffect(() => {
  if (isDemoToken(token)) {
   const demoEvents = getDemoEvents()
   const demoWallet = getDemoWallet()
   setEvents(demoEvents.slice(0, 5))
   setBalance(demoWallet.balance)
   setPlayerStats(getDemoPlayerStats())
   return
  }
  getEvents().then((res) => setEvents(res.slice(0, 5))).catch(() => setEvents([]))

  if (effectiveRole === 'player' && token) {
   getWalletMe(token).then((res) => setBalance(res.balance)).catch(() => {})
   getMyStats(token).then(setPlayerStats).catch(() => {})
  }

  if (effectiveRole === 'partner' && token) {
   getVenues().then((list) => {
    const own = list.filter((v) => v.partner_user_id === user.id)
    setVenues(own)
   }).catch(() => {})
   adminGetPartnerStats(token).then(setPartnerStats).catch(() => {})
  }

  if (effectiveRole === 'admin' && token) {
   adminGetUsers(token, 'player').then(setPlayers).catch(() => {})
   adminGetUsers(token, 'partner').then(setPartners).catch(() => {})
   getVenues().then(setVenues).catch(() => {})
   adminGetTransactions(token).then(setTransactions).catch(() => {})
  }
 }, [token, user, effectiveRole])

 const getSportIcon = (name) => {
  if (!name) return 'game'
  const n = name.toLowerCase()
  if (n.includes('football') || n.includes('soccer')) return 'football'
  if (n.includes('basketball')) return 'basketball'
  if (n.includes('volleyball')) return 'volleyball'
  if (n.includes('tennis')) return 'tennis'
  return 'game'
 }

 const sportIconMap = {
  game: '🎮',
  football: '⚽',
  basketball: '🏀',
  volleyball: '🏐',
  tennis: '🎾',
 }

 if (effectiveRole === 'partner') {
  const stats = partnerStats || {
   total_bookings: 0,
   total_revenue: 0,
   revenue_today: 0,
   revenue_week: 0,
   revenue_month: 0,
   upcoming_games: 0,
   venues_count: venues.length,
   recent_bookings: [],
  }

  return (
   <div className="dashboard-page">
    <div className="dashboard-toolbar">
     <div className="dashboard-toolbar-label">
      {i18n.language.startsWith('ru') ? 'Язык интерфейса' : 'Interface language'}
     </div>
     <LanguageSwitcher className="dashboard-toolbar-switcher" />
    </div>

    <div className="page-header">
     <div className="page-header-copy">
      <h1>{t('dashboard.partnerWelcome')}</h1>
      <p className="page-subtitle">{t('dashboard.partnerSubtitle', { name: displayName })}</p>
     </div>
     <Link to="/partner/venues" className="btn-primary glass-btn page-header-action">🏟️ {t('dashboard.manageVenues')}</Link>
    </div>

    <div className="stats-grid">
     <div className="stat-card glass-card"><div className="stat-card-icon">📅</div><div className="stat-card-value">{stats.total_bookings}</div><div className="stat-card-label">{t('dashboard.totalBookings')}</div></div>
     <div className="stat-card glass-card"><div className="stat-card-icon">🎮</div><div className="stat-card-value">{stats.upcoming_games}</div><div className="stat-card-label">{t('dashboard.upcomingGamesStat')}</div></div>
     <div className="stat-card glass-card"><div className="stat-card-icon">💰</div><div className="stat-card-value gold">{stats.total_revenue}</div><div className="stat-card-label">{t('dashboard.revenue')}</div></div>
     <div className="stat-card glass-card"><div className="stat-card-icon">🏟️</div><div className="stat-card-value">{stats.venues_count}</div><div className="stat-card-label">{t('dashboard.venues')}</div></div>
    </div>

    <div className="dashboard-card glass-card revenue-analytics-card">
     <div className="card-header">
      <h3>{t('dashboard.revenueAnalytics')}</h3>
     </div>
     <div className="revenue-analytics-grid">
      <div className="revenue-analytics-item">
       <span className="revenue-analytics-label">{t('dashboard.revenueToday')}</span>
       <span className="revenue-analytics-value">{stats.revenue_today} {t('common.creditsUnit')}</span>
      </div>
      <div className="revenue-analytics-item">
       <span className="revenue-analytics-label">{t('dashboard.revenueWeek')}</span>
       <span className="revenue-analytics-value">{stats.revenue_week} {t('common.creditsUnit')}</span>
      </div>
      <div className="revenue-analytics-item">
       <span className="revenue-analytics-label">{t('dashboard.revenueMonth')}</span>
       <span className="revenue-analytics-value">{stats.revenue_month} {t('common.creditsUnit')}</span>
      </div>
     </div>
    </div>

    <div className="dashboard-grid">
     <div className="dashboard-card glass-card">
      <div className="card-header"><h3>{t('dashboard.recentBookings')}</h3><Link to="/partner/calendar" className="card-link">{t('dashboard.viewCalendar')}</Link></div>
      <div className="booking-list">
       {stats.recent_bookings.slice(0, 5).map((b) => (
        <div key={b.event_id} className="booking-item">
         <div className="booking-thumb">{sportIconMap[getSportIcon(b.sport_name)]}</div>
         <div className="booking-info">
          <span className="booking-venue">{b.sport_name} @ {b.venue_name}</span>
          <span className="booking-date">{new Date(b.start_at).toLocaleDateString()}</span>
         </div>
         <div className="booking-amount">{b.revenue} {t('common.creditsUnit')}</div>
         <span className={`booking-status ${b.status}`}>{b.status}</span>
        </div>
       ))}
       {stats.recent_bookings.length === 0 && <p className="empty-text">{t('dashboard.noBookings')}</p>}
      </div>
     </div>
     <div className="dashboard-card glass-card venue-highlight">
      <div className="card-header"><h3>{t('dashboard.quickActions')}</h3></div>
      <div className="quick-actions">
       <Link to="/partner/venues" className="quick-action-btn glass-btn">{t('dashboard.addNewVenue')}</Link>
       <Link to="/partner/calendar" className="quick-action-btn glass-btn">{t('dashboard.viewCalendar')}</Link>
      </div>
     </div>
    </div>
   </div>
  )
 }

 if (effectiveRole === 'admin') {
  return (
   <div className="dashboard-page">
    <div className="page-header">
     <div className="page-header-copy">
      <h1>{t('dashboard.adminDashboard')}</h1>
      <p className="page-subtitle">{t('dashboard.adminSubtitle')}</p>
     </div>
    </div>
    <div className="stats-grid">
     <div className="stat-card glass-card"><div className="stat-card-icon">👥</div><div className="stat-card-value">{players.length + partners.length}</div><div className="stat-card-label">{t('dashboard.totalUsers')}</div></div>
     <div className="stat-card glass-card"><div className="stat-card-icon">🎮</div><div className="stat-card-value">{events.length}</div><div className="stat-card-label">{t('dashboard.activeGames')}</div></div>
     <div className="stat-card glass-card"><div className="stat-card-icon">🏟️</div><div className="stat-card-value">{venues.length}</div><div className="stat-card-label">{t('dashboard.venues')}</div></div>
     <div className="stat-card glass-card"><div className="stat-card-icon">💰</div><div className="stat-card-value gold">{transactions.reduce((sum, tx) => sum + (tx.tx_type === 'grant' ? tx.amount : 0), 0)}</div><div className="stat-card-label">{t('dashboard.totalCredits')}</div></div>
    </div>
    <div className="dashboard-grid">
     <div className="dashboard-card glass-card">
      <div className="card-header"><h3>{t('dashboard.quickActions')}</h3></div>
      <div className="quick-actions">
       <Link to="/admin" className="quick-action-btn glass-btn">{t('dashboard.walletControl')}</Link>
       <Link to="/games" className="quick-action-btn glass-btn">{t('dashboard.viewGames')}</Link>
      </div>
     </div>
    </div>
   </div>
  )
 }

 return (
  <div className="dashboard-page">
   <div className="page-header">
    <div className="page-header-copy">
     <h1>{t('dashboard.welcome', { name: getUserDisplayName(user, t('role.player')) })}</h1>
     <p className="page-subtitle">{t('dashboard.subtitle')}</p>
    </div>
    <Link to="/games/create" className="btn-primary glass-btn page-header-action">{t('nav.createGame')}</Link>
   </div>

   <div className="stats-grid">
    <div className="stat-card glass-card"><div className="stat-card-icon">🎮</div><div className="stat-card-value">{playerStats.games_played}</div><div className="stat-card-label">{t('dashboard.gamesJoined')}</div></div>
    <div className="stat-card glass-card"><div className="stat-card-icon">💰</div><div className="stat-card-value gold">{playerStats.balance || balance}</div><div className="stat-card-label">{t('dashboard.credits')}</div></div>
    <div className="stat-card glass-card"><div className="stat-card-icon">🏆</div><div className="stat-card-value">{events.length}</div><div className="stat-card-label">{t('dashboard.availableGames')}</div></div>
    <div className="stat-card glass-card"><div className="stat-card-icon">⭐</div><div className="stat-card-value gold">{Number(playerStats.player_rating || 0).toFixed(1)}</div><div className="stat-card-label">{t('dashboard.rating')}</div></div>
   </div>

   <div className="dashboard-grid">
    <div className="dashboard-card glass-card">
     <div className="card-header"><h3>{t('dashboard.upcomingGames')}</h3><Link to="/games" className="card-link">{t('dashboard.viewAll')}</Link></div>
     <div className="games-list">
      {events.map((event) => (
       <Link key={event.id} to={`/games/${event.id}`} className="game-list-item">
        <div className="game-list-thumb">{sportIconMap[getSportIcon(event.sport_name)]}</div>
        <div className="game-list-info">
         <span className="game-list-title">{event.sport_name || ''} {event.title || t('common.game')}</span>
         <span className="game-list-venue">{event.venue_name || t('common.venue')} • {event.venue_city || ''}</span>
        </div>
        <span className={`game-list-status ${event.current_players >= event.required_players ? 'full' : 'open'}`}>
         {event.current_players >= event.required_players ? t('games.full') : `${event.current_players}/${event.required_players}`}
        </span>
       </Link>
      ))}
      {events.length === 0 && <p className="empty-text">{t('dashboard.noUpcomingGames')}</p>}
     </div>
    </div>

    <div className="dashboard-card glass-card wallet-card">
     <div className="wallet-balance">
      <span className="wallet-label">{t('dashboard.walletBalance')}</span>
      <span className="wallet-amount">{playerStats.balance || balance}</span>
      <span className="wallet-credits">{t('dashboard.creditsAvailable')}</span>
     </div>
     <Link to="/wallet" className="btn-secondary glass-btn">{t('dashboard.addCredits')}</Link>
    </div>
   </div>

   {playerStats.onboarding_score ? (
    <p className="dashboard-footnote">
     {i18n.language.startsWith('ru') ? 'Рейтинг определён по опросу и будет меняться со временем.'
      : 'Your rating was set from the survey and will update over time.'}
    </p>
   ) : null}
  </div>
 )
}

