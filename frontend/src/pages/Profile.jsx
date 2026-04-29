import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { getSports } from '../api/sports'
import { getMyGames, getMyStats, updateProfile } from '../api/users'
import LanguageSwitcher from '../components/LanguageSwitcher'
import UserAvatar from '../components/UserAvatar'
import { PLAYER_AVATAR_OPTIONS } from '../constants/avatarOptions'
import { getOnboardingSubmission } from '../utils/onboarding'
import { getDemoPlayerStats, getDemoProfileGames, getDemoSports, isDemoToken, updateDemoProfile } from '../demo/demoData'
import { getUserDisplayName } from '../utils/userDisplay'

export default function Profile({ user, token, onUserUpdate, effectiveRole, onViewModeChange }) {
 const [stats, setStats] = useState({ games_played: 0, balance: 0, player_rating: 0, onboarding_score: null })
 const [games, setGames] = useState({ created_games: [], completed_games: [], cancelled_games: [] })
 const [gamesTab, setGamesTab] = useState('created')
 const [isEditOpen, setIsEditOpen] = useState(false)
 const [sports, setSports] = useState([])
 const [form, setForm] = useState({
  photo_url: user.photo_url || '',
  bio: user.bio || '',
  favorite_sports: user.favorite_sports || '',
 })
 const [success, setSuccess] = useState('')
 const [error, setError] = useState('')
 const [onboardingResult, setOnboardingResult] = useState(() => getOnboardingSubmission(user).evaluation || null)
 const { t, i18n } = useTranslation()
 const navigate = useNavigate()

 useEffect(() => {
  if (isDemoToken(token)) {
   setStats(getDemoPlayerStats())
   setGames(getDemoProfileGames())
   setSports(getDemoSports())
   return
  }
  if (token) {
   getMyStats(token).then(setStats).catch(() => {})
   getMyGames(token).then(setGames).catch(() => {})
   getSports().then(setSports).catch(() => {})
  }
 }, [token])

 useEffect(() => {
  if (user) {
   setForm({
    photo_url: user.photo_url || '',
    bio: user.bio || '',
    favorite_sports: user.favorite_sports || '',
   })
   setOnboardingResult(getOnboardingSubmission(user).evaluation || null)
  }
 }, [user])

 const handleSave = async (e) => {
  e.preventDefault()
  setError('')
  setSuccess('')
  try {
   const updatedUser = isDemoToken(token)
    ?
     await Promise.resolve(updateDemoProfile(form))
    : await updateProfile(token, form)
   onUserUpdate?.(updatedUser)
   if (isDemoToken(token)) {
    setStats(getDemoPlayerStats())
   }
   setSuccess(t('profile.updated'))
   setIsEditOpen(false)
  } catch (err) {
   setError(err.message)
  }
 }

 const getSportIcon = (name) => {
  if (!name) return '🎮'
  const n = name.toLowerCase()
  if (n.includes('football')) return '⚽'
  if (n.includes('basketball')) return '🏀'
  if (n.includes('volleyball')) return '🏐'
  if (n.includes('tennis')) return '🎾'
  return '🎮'
 }

 const getSportLabel = (name) => {
  if (!name) return t('common.game')
  const n = name.toLowerCase()
  if (n.includes('football') || n.includes('soccer')) return t('welcome.football')
  if (n.includes('basketball')) return t('welcome.basketball')
  if (n.includes('volleyball')) return t('welcome.volleyball')
  if (n.includes('tennis')) return t('games.tennis')
  if (n.includes('padel')) return t('games.padel')
  return name
 }

 const selectedSports = form.favorite_sports ? form.favorite_sports.split(',').filter(Boolean) : []
 const isPlayer = effectiveRole === 'player'
 const canSwitchAdminMode = user.is_admin && user.role === 'player'
 const displayName = getUserDisplayName(user, t('role.player'))

 const toggleSport = (sportId) => {
  const id = String(sportId)
  const updated = selectedSports.includes(id)
   ?
    selectedSports.filter(s => s !== id)
   : [...selectedSports, id]
  setForm({ ...form, favorite_sports: updated.join(',') })
 }

 const handleViewModeChange = (mode) => {
  onViewModeChange?.(mode)
  navigate(mode === 'admin' ? '/admin' : '/dashboard')
 }

 const gameTabs = [
  { key: 'created', label: t('profile.createdGames'), items: games.created_games || [] },
  { key: 'completed', label: t('profile.completedGames'), items: games.completed_games || [] },
  { key: 'cancelled', label: t('profile.cancelledGames'), items: games.cancelled_games || [] },
 ]
 const activeGames = gameTabs.find((tab) => tab.key === gamesTab).items || []
 const gameStatusLabel = (status, event) => {
  if (status === 'completed' && event.current_players < event.required_players) return t('profile.notHeld')
  return t(`admin.${status}`)
 }
 const displayRating = Number.isFinite(Number(stats.player_rating))
  ?
   Number(stats.player_rating).toFixed(1)
  : '0.0'

 return (
  <div className="dashboard-page profile-page">
   <div className="page-header">
    <div className="page-header-copy">
     <h1>{t('profile.title')}</h1>
     <p className="page-subtitle">{t('profile.subtitle')}</p>
    </div>
   </div>

   <div className="profile-overview">
    <div className="dashboard-card glass-card profile-summary-card">
     <div className="profile-avatar-wrap">
      <UserAvatar
       user={user}
       src={form.photo_url}
       alt={t('nav.profile')}
       className="user-avatar-small profile-summary-avatar"
       size={96}
      />
     </div>
     <h2 className="profile-summary-name">{displayName}</h2>
     <p className="profile-summary-email">{user.email}</p>
     <p className="profile-summary-role">{t(`role.${effectiveRole || user.role || 'player'}`)}</p>

     <div className="profile-summary-stats" role="list" aria-label={t('profile.title')}>
      <div className="profile-inline-stat" role="listitem">
       <div className="profile-inline-stat-value">{stats.games_played}</div>
       <div className="profile-inline-stat-label">{t('leaderboard.games')}</div>
      </div>
      <span className="profile-inline-divider" aria-hidden="true" />
      <div className="profile-inline-stat" role="listitem">
       <div className="profile-inline-stat-value gold">{stats.balance}</div>
       <div className="profile-inline-stat-label">{t('dashboard.credits')}</div>
      </div>
     </div>

     <div className="profile-summary-actions">
      <button
       type="button"
       className={`btn-primary glass-btn profile-edit-toggle ${isEditOpen ? 'active' : ''}`}
       onClick={() => setIsEditOpen((current) => !current)}
       aria-expanded={isEditOpen}
       aria-controls="profile-edit-panel"
      >
       {isEditOpen ? t('chat.close') : t('profile.editProfile')}
      </button>
     </div>

     <div className="profile-meta-strip">
      {isPlayer && (
       <div className="profile-meta-pill">
        <span className="profile-meta-pill-label">{t('dashboard.rating')}</span>
        <span className="profile-meta-pill-value">{displayRating}</span>
       </div>
      )}

      <div className="glass-card profile-info-card profile-language-card">
       <div className="profile-info-label profile-language-label">
        {i18n.language.startsWith('ru') ? 'Язык интерфейса' : 'Interface language'}
       </div>
       <LanguageSwitcher className="profile-language-switcher" fullWidth />
      </div>

      {canSwitchAdminMode && (
       <div className="glass-card profile-info-card profile-mode-card">
        <div className="profile-info-label profile-mode-label">
         {t('profile.accountMode')}
        </div>
        <div className="profile-mode-switch">
         <button
          type="button"
          className={`btn-secondary glass-btn ${effectiveRole === 'player' ? 'active' : ''}`}
          onClick={() => handleViewModeChange('player')}
         >
          {t('profile.playerMode')}
         </button>
         <button
          type="button"
          className={`btn-secondary glass-btn ${effectiveRole === 'admin' ? 'active' : ''}`}
          onClick={() => handleViewModeChange('admin')}
         >
          {t('profile.adminMode')}
         </button>
        </div>
       </div>
      )}
     </div>

     {onboardingResult && (
      <div className="profile-rating-note">
       <div className="profile-info-note">
        {i18n.language.startsWith('ru') ? 'Рейтинг определён по опросу и может меняться со временем.'
         : 'Your rating was set from the survey and may update over time.'}
       </div>
      </div>
     )}
    </div>
   </div>

   <section
    id="profile-edit-panel"
    className={`dashboard-card glass-card profile-edit-card ${isEditOpen ? 'is-open' : ''}`}
    hidden={!isEditOpen}
   >
    <div className="profile-edit-header">
     <div>
      <h3>{t('profile.editProfile')}</h3>
      <p className="profile-edit-subtitle">{t('profile.subtitle')}</p>
     </div>
    </div>
    <form onSubmit={handleSave} className="grant-form profile-edit-form">
     <div className="profile-form-grid">
      <div className="form-group">
       <label>{t('auth.firstName')}</label>
       <input type="text" value={user.first_name || ''} disabled />
      </div>
      <div className="form-group">
       <label>{t('auth.lastName')}</label>
       <input type="text" value={user.last_name || ''} disabled />
      </div>
     </div>
     {isPlayer ? (
      <div className="form-group">
       <label>{t('profile.avatarChoice')}</label>
       <div className="avatar-picker-grid profile-avatar-picker">
        {PLAYER_AVATAR_OPTIONS.map((option, index) => (
         <button
          key={option.id}
          type="button"
          className={`avatar-option-card ${form.photo_url === option.src ? 'active' : ''}`}
          onClick={() => setForm({ ...form, photo_url: option.src })}
         >
          <img src={option.src} alt={`${t('profile.avatarOption')} ${index + 1}`} className="avatar-option-image" />
          <span>{t('profile.avatarOption')} {index + 1}</span>
         </button>
        ))}
       </div>
      </div>
     ) : (
      <div className="form-group">
       <label>{t('profile.photoUrl')}</label>
       <input
        type="url"
        placeholder={t('profile.photoPlaceholder')}
        value={form.photo_url}
        onChange={(e) => setForm({ ...form, photo_url: e.target.value })}
       />
      </div>
     )}
     <div className="form-group">
      <label>{t('profile.bio')}</label>
      <textarea
       className="profile-textarea"
       placeholder={t('profile.bioPlaceholder')}
       value={form.bio}
       onChange={(e) => setForm({ ...form, bio: e.target.value })}
       rows={4}
      />
     </div>
     <div className="form-group">
      <label>{t('profile.favSports')}</label>
      <div className="profile-sports-list">
       {sports.map(s => (
        <button
         key={s.id}
         type="button"
         className={`sport-tab ${selectedSports.includes(String(s.id)) ? 'active' : ''}`}
         onClick={() => toggleSport(s.id)}
        >
         {getSportIcon(s.name)} {getSportLabel(s.name)}
        </button>
       ))}
      </div>
     </div>
     {error && <div className="alert alert-error">{error}</div>}
     {success && <div className="alert alert-success">{success}</div>}
     <div className="profile-edit-footer">
      <button type="submit" className="btn-primary profile-save-btn">{t('profile.save')}</button>
     </div>
    </form>
   </section>

   <div className="dashboard-card glass-card profile-games-card">
    <div className="profile-games-header">
     <div>
      <h3 className="profile-games-title">{t('profile.gamesBlockTitle')}</h3>
      <p className="profile-games-subtitle">{t('profile.gamesBlockSubtitle')}</p>
     </div>
     <div className="profile-games-tabs" role="tablist" aria-label={t('profile.gamesBlockTitle')}>
      {gameTabs.map((tab) => (
       <button
        key={tab.key}
        type="button"
        className={`sport-tab ${gamesTab === tab.key ? 'active' : ''}`}
        onClick={() => setGamesTab(tab.key)}
        role="tab"
        aria-selected={gamesTab === tab.key}
       >
        {tab.label} ({tab.items.length})
       </button>
      ))}
     </div>
    </div>

    {activeGames.length === 0 ? (
     <div className="empty-state glass-card profile-games-empty">
      <span className="empty-icon">🎮</span>
      <h3>{t('profile.noGamesInSection')}</h3>
      <p>{t('profile.noGamesInSectionHint')}</p>
     </div>
    ) : (
     <div className="profile-games-list">
      {activeGames.map((event) => (
       <div key={event.id} className="glass-card profile-game-item">
        <div className="profile-game-item-head">
         <div>
          <div className="profile-game-item-title">{event.title}</div>
          <div className="profile-game-item-meta">
           {event.sport_name || t('common.game')} • {event.venue_name || t('common.venue')} • {event.venue_city || 'Bishkek'}
          </div>
         </div>
         <span className={`status-badge ${event.status}`}>{gameStatusLabel(event.status, event)}</span>
        </div>
        <div className="profile-game-item-details">
         <span>📅 {new Date(event.start_at).toLocaleString()}</span>
         <span>👥 {event.current_players}/{event.required_players}</span>
        </div>
        <div className="profile-game-item-action">
         <Link to={`/games/${event.id}`} className="btn-secondary glass-btn">
          {t('games.viewDetails')}
         </Link>
        </div>
       </div>
      ))}
     </div>
    )}
   </div>
  </div>
 )
}

