import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useParams } from 'react-router-dom'
import { getEvent, joinEvent, leaveEvent, registerTournamentTeam } from '../api/events'
import { getDemoEvent, isDemoToken, joinDemoEvent, leaveDemoEvent } from '../demo/demoData'
import { getParticipantDisplayName } from '../utils/userDisplay'

function buildTournamentMembers(count, currentMembers = [], captainFirstName = '', captainLastName = '') {
 const safeCount = Number(count)
 if (!Number.isInteger(safeCount) || safeCount < 1) {
  return []
 }
 return Array.from({ length: safeCount }, (_, index) => {
  if (index === 0) {
   return {
    first_name: captainFirstName,
    last_name: captainLastName,
    is_captain: true,
   }
  }
  const existing = currentMembers[index] || {}
  return {
   first_name: existing.first_name || '',
   last_name: existing.last_name || '',
   is_captain: false,
  }
 })
}

export default function GameDetails({ token, user, effectiveRole }) {
 const { id } = useParams()
 const [event, setEvent] = useState(null)
 const [teamNumber, setTeamNumber] = useState('')
 const [error, setError] = useState('')
 const [submittingJoin, setSubmittingJoin] = useState(false)
 const [submittingLeave, setSubmittingLeave] = useState(false)
 const [submittingTournament, setSubmittingTournament] = useState(false)
 const [tournamentForm, setTournamentForm] = useState({
  team_name: '',
  team_slogan: '',
  captain_first_name: '',
  captain_last_name: '',
  captain_phone: '',
  players_count: '',
  members: [],
 })
 const { t, i18n } = useTranslation()

 const load = () => {
  if (isDemoToken(token)) {
   try {
    setEvent(getDemoEvent(id))
    setError('')
   } catch (e) {
    setError(e.message)
   }
   return Promise.resolve()
  }
  return getEvent(id).then(setEvent).catch((e) => setError(e.message))
 }

 useEffect(() => { load() }, [id, token])

 useEffect(() => {
  if (!event || event.event_type !== 'tournament') return
  setTournamentForm({
   team_name: '',
   team_slogan: '',
   captain_first_name: '',
   captain_last_name: '',
   captain_phone: '',
   players_count: '',
   members: [],
  })
 }, [event])

 const myParticipant = useMemo(
  () => event?.participants?.find((p) => p.user_id === user.id && p.status === 'joined') || null,
  [event, user],
 )

 const getSportIcon = (name) => {
  if (!name) return '🎮'
  const n = name.toLowerCase()
  if (n.includes('football') || n.includes('soccer')) return '⚽'
  if (n.includes('basketball')) return '🏀'
  if (n.includes('volleyball')) return '🏐'
  if (n.includes('tennis')) return '🎾'
  return '🎮'
 }

 const getSportLabel = (name) => {
  if (!name) return t('common.game')
  const normalized = String(name).toLowerCase()
  if (normalized.includes('football') || normalized.includes('soccer') || normalized.includes('футбол')) return t('welcome.football')
  if (normalized.includes('basketball') || normalized.includes('баскетбол')) return t('welcome.basketball')
  if (normalized.includes('volleyball') || normalized.includes('волейбол')) return t('welcome.volleyball')
  return name
 }

 const join = async () => {
  setError('')
  setSubmittingJoin(true)
  try {
   if (isDemoToken(token)) {
    await Promise.resolve(joinDemoEvent(id, user, { team_number: teamNumber ? Number(teamNumber) : null }))
   } else {
    await joinEvent(token, id, { team_number: teamNumber ? Number(teamNumber) : null })
   }
   await load()
  } catch (e) {
   setError(e.message)
  } finally {
   setSubmittingJoin(false)
  }
 }

 const leave = async () => {
  setError('')
  setSubmittingLeave(true)
  try {
   if (isDemoToken(token)) {
    await Promise.resolve(leaveDemoEvent(id))
   } else {
    await leaveEvent(token, id)
   }
   setTeamNumber('')
   await load()
  } catch (e) {
   setError(e.message)
  } finally {
   setSubmittingLeave(false)
  }
 }

 const updateTournamentCaptain = (field, value) => {
  setTournamentForm((current) => {
   const next = { ...current, [field]: value }
   next.members = buildTournamentMembers(
    next.players_count,
    current.members,
    field === 'captain_first_name' ? value : next.captain_first_name,
    field === 'captain_last_name' ? value : next.captain_last_name,
   )
   return next
  })
 }

 const updateTournamentPlayersCount = (value) => {
  const normalized = value === '' ? '' : String(Math.max(0, Number(value) || 0))
  setTournamentForm((current) => ({
   ...current,
   players_count: normalized,
   members: buildTournamentMembers(
    normalized,
    current.members,
    current.captain_first_name,
    current.captain_last_name,
   ),
  }))
 }

 const updateTournamentMember = (index, field, value) => {
  if (index === 0) return
  setTournamentForm((current) => ({
   ...current,
   members: current.members.map((member, memberIndex) => (
    memberIndex === index ? { ...member, [field]: value } : member
   )),
  }))
 }

 const registerTeam = async (e) => {
  e.preventDefault()
  setError('')
  setSubmittingTournament(true)
  try {
   const playersCount = Number.parseInt(tournamentForm.players_count, 10)
   if (!Number.isInteger(playersCount) || playersCount < 1) {
    throw new Error(t('gameDetails.playersCountRequired'))
   }
   const payload = {
    team_name: tournamentForm.team_name,
    team_slogan: tournamentForm.team_slogan,
    captain_first_name: tournamentForm.captain_first_name,
    captain_last_name: tournamentForm.captain_last_name,
    captain_phone: tournamentForm.captain_phone,
    players_count: playersCount,
    members: buildTournamentMembers(
     playersCount,
     tournamentForm.members,
     tournamentForm.captain_first_name,
     tournamentForm.captain_last_name,
    ),
   }
   await registerTournamentTeam(token, id, payload)
   await load()
  } catch (e) {
   setError(e.message)
  } finally {
   setSubmittingTournament(false)
  }
 }

 if (!event) return <div className="dashboard-page"><p className="empty-text">{t('gameDetails.loading')}</p></div>

 const joinedParticipants = event.participants.filter(p => p.status === 'joined') || []
 const progressPct = (joinedParticipants.length / event.required_players) * 100
 const isFull = joinedParticipants.length >= event.required_players
 const tournamentRegistrations = event.tournament_registrations || []
 const tournamentProgress = event.teams_count > 0 ? (tournamentRegistrations.length / event.teams_count) * 100 : 0

 const getParticipantLabel = (participant) => {
  return getParticipantDisplayName(participant, t('role.player'))
 }

 if (event.event_type === 'tournament') {
  return (
   <div className="dashboard-page">
    <div className="page-header">
     <div>
      <h1>{getSportIcon(event.sport_name)} {event.title}</h1>
      <p className="page-subtitle">{event.venue_name} • {event.venue_city} • {t('games.teamRegistration')}</p>
     </div>
     <div className="game-details-badge-stack">
      <span className={`status-badge ${event.status}`}>{t(`admin.${event.status}`)}</span>
      <span className={`status-badge ${event.registration_is_closed ? 'registration-closed' : 'registration-open'}`}>
       {event.registration_is_closed ? t('games.registrationClosed') : t('games.registrationOpen')}
      </span>
     </div>
    </div>

    <div className="stats-grid">
     <div className="stat-card glass-card">
      <div className="stat-card-icon">📅</div>
      <div className="stat-card-value" style={{ fontSize: '1rem' }}>{new Date(event.start_at).toLocaleDateString(i18n.language === 'ru' ? 'ru-RU' : 'en-US', { weekday: 'short', month: 'short', day: 'numeric' })}</div>
      <div className="stat-card-label">{new Date(event.start_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} - {new Date(event.end_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
     </div>
     <div className="stat-card glass-card">
      <div className="stat-card-icon">🏁</div>
      <div className="stat-card-value">{tournamentRegistrations.length}/{event.teams_count}</div>
      <div className="stat-card-label">{t('games.teamsLabel')}</div>
     </div>
     <div className="stat-card glass-card">
      <div className="stat-card-icon">⏳</div>
      <div className="stat-card-value" style={{ fontSize: '1rem' }}>{new Date(event.registration_deadline).toLocaleDateString(i18n.language === 'ru' ? 'ru-RU' : 'en-US', { day: 'numeric', month: 'short' })}</div>
      <div className="stat-card-label">{t('games.registrationDeadline')}</div>
     </div>
     <div className="stat-card glass-card">
      <div className="stat-card-icon">💰</div>
      <div className="stat-card-value gold">{event.entry_fee_credits_team}</div>
      <div className="stat-card-label">{t('games.creditsPerTeam')}</div>
     </div>
    </div>

    <div className="dashboard-card glass-card game-details-progress-card" style={{ marginBottom: '1.5rem' }}>
     <div className="game-details-progress-head">
      <span>{t('gameDetails.teamSlotsFilled')}</span>
      <span style={{ color: 'var(--gold)' }}>{tournamentRegistrations.length}/{event.teams_count}</span>
     </div>
     <div className="game-card-progress" style={{ height: '8px' }}>
      <div className="progress-bar" style={{ width: `${tournamentProgress}%` }}></div>
     </div>
    </div>

    <div className="dashboard-card glass-card" style={{ marginBottom: '1.5rem' }}>
     <h3>{t('gameDetails.venueDetails')}</h3>
     <div className="game-details-venue-grid">
      <div><strong>{t('gameDetails.venue')}</strong> {event.venue_name}</div>
      <div><strong>{t('gameDetails.city')}</strong> {event.venue_city}</div>
      <div><strong>{t('gameDetails.address')}</strong> {event.venue_address}</div>
      <div><strong>{t('gameDetails.sport')}</strong> {getSportIcon(event.sport_name)} {getSportLabel(event.sport_name)}</div>
     </div>
    </div>

    <div className="dashboard-card glass-card" style={{ marginBottom: '1.5rem' }}>
     <h3>{t('gameDetails.tournamentInfo')}</h3>
     <div className="game-details-venue-grid">
      <div><strong>{t('gameDetails.entryFeePerTeam')}</strong> {event.entry_fee_credits_team} {t('games.creditsLabel')}</div>
      <div><strong>{t('gameDetails.registrationDeadlineLabel')}</strong> {formatDateTime(event.registration_deadline, i18n.language)}</div>
      <div><strong>{t('gameDetails.teamGoal')}</strong> {event.teams_count}</div>
      <div><strong>{t('gameDetails.registrationStatus')}</strong> {event.registration_is_closed ? t('games.registrationClosed') : t('games.registrationOpen')}</div>
     </div>
     {event.description ? <p className="game-details-description">{event.description}</p> : null}
    </div>

    <div className="dashboard-card glass-card" style={{ marginBottom: '1.5rem' }}>
     <h3>{t('gameDetails.registeredTeams')}</h3>
     {tournamentRegistrations.length === 0 ? (
      <p className="empty-text">{t('gameDetails.noRegisteredTeams')}</p>
     ) : (
      <div className="game-details-tournament-grid">
       {tournamentRegistrations.map((registration) => (
        <div key={registration.id} className="game-details-tournament-card">
         <div className="game-details-tournament-head">
          <div>
           <strong>{registration.team_name}</strong>
           <p>{registration.team_slogan || t('gameDetails.noTeamSlogan')}</p>
          </div>
          <span>{registration.players_count} {t('gameDetails.playersCountShort')}</span>
         </div>
        </div>
       ))}
      </div>
     )}
    </div>

    {effectiveRole === 'player' && event.status === 'active' && (
     <div className="dashboard-card glass-card game-details-join-card" style={{ marginTop: '1.5rem' }}>
      {!event.registration_is_closed ? (
       <form className="game-details-tournament-form" onSubmit={registerTeam}>
        <div className="game-details-form-grid">
         <div className="form-group">
          <label>{t('gameDetails.teamName')}</label>
          <input
           type="text"
           value={tournamentForm.team_name}
           onChange={(e) => setTournamentForm((current) => ({ ...current, team_name: e.target.value }))}
           placeholder={t('gameDetails.teamNamePlaceholder')}
           required
          />
         </div>
         <div className="form-group">
          <label>{t('gameDetails.teamSlogan')}</label>
          <input
           type="text"
           value={tournamentForm.team_slogan}
           onChange={(e) => setTournamentForm((current) => ({ ...current, team_slogan: e.target.value }))}
           placeholder={t('gameDetails.teamSloganPlaceholder')}
          />
         </div>
         <div className="form-group">
          <label>{t('auth.firstName')}</label>
          <input
           type="text"
           value={tournamentForm.captain_first_name}
           onChange={(e) => updateTournamentCaptain('captain_first_name', e.target.value)}
           placeholder={t('auth.firstNamePlaceholder')}
           required
          />
         </div>
         <div className="form-group">
          <label>{t('auth.lastName')}</label>
          <input
           type="text"
           value={tournamentForm.captain_last_name}
           onChange={(e) => updateTournamentCaptain('captain_last_name', e.target.value)}
           placeholder={t('auth.lastNamePlaceholder')}
           required
          />
         </div>
         <div className="form-group">
          <label>{t('gameDetails.phone')}</label>
          <input
           type="tel"
           value={tournamentForm.captain_phone}
           onChange={(e) => setTournamentForm((current) => ({ ...current, captain_phone: e.target.value }))}
           placeholder="+996 555 00 00 00"
           required
          />
         </div>
         <div className="form-group">
          <label>{t('gameDetails.playersCount')}</label>
          <input
           type="number"
           min="1"
           max="100"
           value={tournamentForm.players_count}
           onChange={(e) => updateTournamentPlayersCount(e.target.value)}
           placeholder="1"
           required
          />
         </div>
        </div>

        <div className="game-details-members-section">
         <h3>{t('gameDetails.roster')}</h3>
         <div className="game-details-members-list">
          {tournamentForm.members.map((member, index) => (
           <div key={`member-${index}`} className="game-details-member-row">
            <span className="game-details-member-index">
             {index === 0 ? t('gameDetails.captain') : `${t('gameDetails.playerLabel')} ${index + 1}`}
            </span>
            <input
             type="text"
             value={member.first_name}
             onChange={(e) => updateTournamentMember(index, 'first_name', e.target.value)}
             placeholder={index === 0 ? t('auth.firstNamePlaceholder') : t('auth.firstNamePlaceholder')}
             readOnly={index === 0}
             required
            />
            <input
             type="text"
             value={member.last_name}
             onChange={(e) => updateTournamentMember(index, 'last_name', e.target.value)}
             placeholder={index === 0 ? t('auth.lastNamePlaceholder') : t('auth.lastNamePlaceholder')}
             readOnly={index === 0}
             required
            />
           </div>
          ))}
         </div>
        </div>

        <div className="game-details-joined-note game-details-tournament-note">
         <span style={{ color: 'var(--gold)' }}>{t('gameDetails.teamPaymentNotice', { credits: event.entry_fee_credits_team })}</span>
         <span style={{ opacity: 0.75 }}>{t('gameDetails.teamPaymentHint')}</span>
        </div>
        <button type="submit" className="btn-primary glass-btn" disabled={submittingTournament}>
         {submittingTournament ? t('gameDetails.registeringTeam') : t('gameDetails.registerTeamCta', { credits: event.entry_fee_credits_team })}
        </button>
       </form>
      ) : (
       <div className="game-details-joined-note">
        <span style={{ color: 'var(--gold)' }}>{t('games.registrationClosed')}</span>
        <span style={{ opacity: 0.75 }}>{t('gameDetails.registrationClosedHint')}</span>
       </div>
      )}
     </div>
    )}

    {error && <div className="alert alert-error" style={{ marginTop: '1rem' }}>{error}</div>}
   </div>
  )
 }

 return (
  <div className="dashboard-page">
   <div className="page-header">
    <div>
     <h1>{getSportIcon(event.sport_name)} {event.title}</h1>
     <p className="page-subtitle">{event.venue_name} • {event.venue_city}</p>
    </div>
    <span className={`status-badge ${event.status}`}>{t(`admin.${event.status}`)}</span>
   </div>

   <div className="stats-grid">
    <div className="stat-card glass-card">
     <div className="stat-card-icon">📅</div>
     <div className="stat-card-value" style={{ fontSize: '1rem' }}>{new Date(event.start_at).toLocaleDateString(i18n.language === 'ru' ? 'ru-RU' : 'en-US', { weekday: 'short', month: 'short', day: 'numeric' })}</div>
     <div className="stat-card-label">{new Date(event.start_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} - {new Date(event.end_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
    </div>
    <div className="stat-card glass-card">
     <div className="stat-card-icon">👥</div>
     <div className="stat-card-value">{joinedParticipants.length}/{event.required_players}</div>
     <div className="stat-card-label">{t('gameDetails.players')}</div>
    </div>
    <div className="stat-card glass-card">
     <div className="stat-card-icon">⏱️</div>
     <div className="stat-card-value">{event.duration_hours}h</div>
     <div className="stat-card-label">{t('gameDetails.duration')}</div>
    </div>
    <div className="stat-card glass-card">
     <div className="stat-card-icon">💰</div>
     <div className="stat-card-value gold">{event.cost_credits_per_player}</div>
     <div className="stat-card-label">{t('gameDetails.creditsPerPlayer')}</div>
    </div>
   </div>

   <div className="dashboard-card glass-card game-details-progress-card" style={{ marginBottom: '1.5rem' }}>
    <div className="game-details-progress-head">
     <span>{t('gameDetails.slotsFilled')}</span>
     <span style={{ color: 'var(--gold)' }}>{joinedParticipants.length}/{event.required_players}</span>
    </div>
    <div className="game-card-progress" style={{ height: '8px' }}>
     <div className="progress-bar" style={{ width: `${progressPct}%` }}></div>
    </div>
   </div>

   <div className="dashboard-card glass-card" style={{ marginBottom: '1.5rem' }}>
    <h3>{t('gameDetails.venueDetails')}</h3>
    <div className="game-details-venue-grid">
     <div><strong>{t('gameDetails.venue')}</strong> {event.venue_name}</div>
     <div><strong>{t('gameDetails.city')}</strong> {event.venue_city}</div>
     <div><strong>{t('gameDetails.address')}</strong> {event.venue_address}</div>
     <div><strong>{t('gameDetails.sport')}</strong> {getSportIcon(event.sport_name)} {getSportLabel(event.sport_name)}</div>
    </div>
   </div>

   <div className="dashboard-card glass-card" style={{ marginBottom: '1.5rem' }}>
    <h3>{i18n.language === 'ru' ? 'Стоимость участия' : 'Participation Pricing'}</h3>
    <div className="game-details-venue-grid">
     <div><strong>{i18n.language === 'ru' ? 'Аренда на игрока:' : 'Rent per player:'}</strong> {event.rent_share_per_player}</div>
     <div><strong>{i18n.language === 'ru' ? 'Комиссия платформы:' : 'Platform fee:'}</strong> {event.platform_fee_per_player}</div>
     <div><strong>{i18n.language === 'ru' ? 'Итого к оплате:' : 'Final player price:'}</strong> {event.cost_credits_per_player}</div>
     <div><strong>{i18n.language === 'ru' ? 'Статус расчета:' : 'Pricing status:'}</strong> {event.pricing_applied ? (i18n.language === 'ru' ? 'применен' : 'applied') : (i18n.language === 'ru' ? 'ожидает добора игроков' : 'waiting for enough players')}</div>
    </div>
   </div>

   <div className="dashboard-grid game-teams-grid">
    {event.teams.map((team) => {
     const teamPlayers = joinedParticipants.filter(p => p.team_id === team.id)
     return (
      <div key={team.id} className="dashboard-card glass-card game-team-card">
       <h3>{t('gameDetails.team')} #{team.team_number}</h3>
       <div className="booking-list game-team-list">
        {teamPlayers.length === 0 ? (
         <p className="empty-text game-team-empty">{t('gameDetails.noPlayersYet')}</p>
        ) : (
         teamPlayers.map(p => (
          <div key={p.id} className="booking-item">
           <div className="user-avatar-small">{getParticipantLabel(p)[0].toUpperCase() || ''}</div>
           <div className="booking-info">
            <span className="booking-venue">{getParticipantLabel(p)}</span>
            <span className="booking-date">{t('dashboard.rating')}: {Number(p.user_rating || 0).toFixed(1)}</span>
           </div>
          </div>
         ))
        )}
       </div>
      </div>
     )
    })}

    {(() => {
     const unassigned = joinedParticipants.filter(p => !p.team_id)
     if (unassigned.length === 0) return null
     return (
      <div className="dashboard-card glass-card game-team-card">
       <h3>{t('gameDetails.noTeam')}</h3>
       <div className="booking-list game-team-list">
        {unassigned.map(p => (
         <div key={p.id} className="booking-item">
          <div className="user-avatar-small">{getParticipantLabel(p)[0].toUpperCase() || ''}</div>
          <div className="booking-info">
           <span className="booking-venue">{getParticipantLabel(p)}</span>
           <span className="booking-date">{t('dashboard.rating')}: {Number(p.user_rating || 0).toFixed(1)}</span>
          </div>
         </div>
        ))}
       </div>
      </div>
     )
    })()}
   </div>

   {effectiveRole === 'player' && event.status === 'active' && (
    <div className="dashboard-card glass-card game-details-join-card" style={{ marginTop: '1.5rem' }}>
     {!myParticipant && !isFull ? (
      <div className="game-details-join-row">
       <select value={teamNumber} onChange={(e) => setTeamNumber(e.target.value)} className="filter-select">
        <option value="">{t('gameDetails.noTeamPref')}</option>
        {event.teams.map((team) => (
         <option key={team.id} value={team.team_number}>{t('gameDetails.team')} #{team.team_number}</option>
        ))}
       </select>
       <button onClick={join} className="btn-primary glass-btn" disabled={submittingJoin}>
        {submittingJoin ? t('common.loading') : t('gameDetails.joinGame', { credits: event.cost_credits_per_player })}
       </button>
      </div>
     ) : !myParticipant && isFull ? (
      <div className="game-details-joined-note">
       <span style={{ color: 'var(--gold)' }}>{t('games.full')}</span>
       <span style={{ opacity: 0.75 }}>{i18n.language === 'ru' ? 'Набор игроков завершен' : 'Joining is closed for this game'}</span>
      </div>
     ) : (
      <div className="game-details-join-row">
       <div className="game-details-joined-note">
        <span style={{ color: 'var(--gold)' }}>{t('gameDetails.youreIn')}</span>
       </div>
       <button onClick={leave} className="btn-secondary glass-btn" disabled={submittingLeave}>
        {submittingLeave ? t('common.loading') : t('gameDetails.leaveGame')}
       </button>
      </div>
     )}
    </div>
   )}

   {error && <div className="alert alert-error" style={{ marginTop: '1rem' }}>{error}</div>}
  </div>
 )
}

function formatDateTime(value, language) {
 if (!value) return '-'
 return new Date(value).toLocaleString(language === 'ru' ? 'ru-RU' : 'en-US', {
  day: 'numeric',
  month: 'short',
  hour: '2-digit',
  minute: '2-digit',
 })
}
