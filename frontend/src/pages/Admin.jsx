import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useLocation } from 'react-router-dom'
import {
 adminCreatePartner,
 adminCreateTournament,
 adminDebitCredits,
 adminDeleteTournamentRegistration,
 adminGetTournamentRegistrations,
 adminGetTransactions,
 adminUpdateTournamentRegistration,
 adminGetUsersWithBalance,
 adminGrantCredits,
 adminRevokeGrant,
 adminSetUserAdminRole,
} from '../api/admin'
import { sendVerificationCode } from '../api/auth'
import { getEvents, updateEvent } from '../api/events'
import { getSports } from '../api/sports'
import { getVenues } from '../api/venues'
import UserAvatar from '../components/UserAvatar'
import { getUserDisplayName } from '../utils/userDisplay'

export default function Admin({ token, user }) {
 const location = useLocation()
 const getInitialTab = () => (location.pathname === '/admin' ? 'wallet' : 'players')
 const [tab, setTab] = useState(getInitialTab)
 const [players, setPlayers] = useState([])
 const [partners, setPartners] = useState([])
 const [sports, setSports] = useState([])
 const [venues, setVenues] = useState([])
 const [events, setEvents] = useState([])
 const [tournaments, setTournaments] = useState([])
 const [tournamentRegistrations, setTournamentRegistrations] = useState({})
 const [registrationSlogans, setRegistrationSlogans] = useState({})
 const [transactions, setTransactions] = useState([])
 const [error, setError] = useState('')
 const [success, setSuccess] = useState('')
 
 // Grant credits form
 const [grantEmail, setGrantEmail] = useState('')
 const [grantAmount, setGrantAmount] = useState('')
 const [grantReason, setGrantReason] = useState('')
 const [walletAction, setWalletAction] = useState('grant')
 const [granting, setGranting] = useState(false)
 const [revokingTransactionId, setRevokingTransactionId] = useState('')
 const [updatingUserId, setUpdatingUserId] = useState('')
 const [emailSearch, setEmailSearch] = useState('')
 const [showSuggestions, setShowSuggestions] = useState(false)
 const [partnerForm, setPartnerForm] = useState({
  first_name: '',
  last_name: '',
  birth_date: '',
  email: '',
  verification_code: '',
  password: '',
 })
 const [creatingPartner, setCreatingPartner] = useState(false)
 const [sendingPartnerCode, setSendingPartnerCode] = useState(false)
 const [partnerCodeSent, setPartnerCodeSent] = useState(false)
 const [tournamentForm, setTournamentForm] = useState({
  title: '',
  sport_id: '',
  venue_id: '',
  start_at: '',
  end_at: '',
  registration_deadline: '',
  teams_count: '8',
  entry_fee_credits_team: '',
  description: '',
  is_featured: true,
 })
 const [creatingTournament, setCreatingTournament] = useState(false)
 const [loadingTournamentRegistrations, setLoadingTournamentRegistrations] = useState(false)
 const [togglingRegistrationEventId, setTogglingRegistrationEventId] = useState('')
 const [removingTournamentRegistrationId, setRemovingTournamentRegistrationId] = useState('')
 const [savingTournamentRegistrationId, setSavingTournamentRegistrationId] = useState('')
 const { t, i18n } = useTranslation()

 // Game filters
 const [gameStatus, setGameStatus] = useState('')
 const [gameFromDate, setGameFromDate] = useState('')
 const [gameToDate, setGameToDate] = useState('')

 useEffect(() => {
  loadData()
 }, [token])

 useEffect(() => {
  setTab(getInitialTab())
 }, [location.pathname])

 const toIsoOrNull = (value) => (value ? new Date(value).toISOString() : null)

 const loadTournamentRegistrations = async (tournamentList) => {
  if (!token || tournamentList.length === 0) {
   setTournamentRegistrations({})
   return
  }
  setLoadingTournamentRegistrations(true)
  try {
   const results = await Promise.all(
    tournamentList.map(async (event) => {
     try {
      const registrations = await adminGetTournamentRegistrations(token, event.id)
      return [event.id, registrations]
     } catch {
      return [event.id, []]
     }
    }),
   )
   const registrationsMap = Object.fromEntries(results)
   setTournamentRegistrations(registrationsMap)
   setRegistrationSlogans(
    Object.fromEntries(
     Object.values(registrationsMap)
      .flat()
      .map((registration) => [registration.id, registration.team_slogan || '']),
    ),
   )
  } finally {
   setLoadingTournamentRegistrations(false)
  }
 }

 const loadGames = () => {
  const filters = { event_type: 'pickup' }
  if (gameStatus) filters.status = gameStatus
  if (gameFromDate) filters.from = new Date(gameFromDate).toISOString()
  if (gameToDate) filters.to = new Date(gameToDate).toISOString()
  getEvents(filters, token).then(setEvents).catch(() => {})
 }

 const loadTournaments = async () => {
  const filters = { event_type: 'tournament' }
  if (gameStatus) filters.status = gameStatus
  if (gameFromDate) filters.from = new Date(gameFromDate).toISOString()
  if (gameToDate) filters.to = new Date(gameToDate).toISOString()
  try {
   const tournamentList = await getEvents(filters, token)
   setTournaments(tournamentList)
   await loadTournamentRegistrations(tournamentList)
  } catch {
   setTournaments([])
   setTournamentRegistrations({})
  }
 }

 const loadData = () => {
  adminGetUsersWithBalance(token, 'player').then(setPlayers).catch(() => {})
  adminGetUsersWithBalance(token, 'partner').then(setPartners).catch(() => {})
  getSports().then(setSports).catch(() => {})
  getVenues().then(setVenues).catch(() => {})
  loadGames()
  loadTournaments()
  adminGetTransactions(token).then(setTransactions).catch(() => {})
 }

 const refreshWalletData = () => {
  adminGetTransactions(token).then(setTransactions).catch(() => {})
  adminGetUsersWithBalance(token, 'player').then(setPlayers).catch(() => {})
  adminGetUsersWithBalance(token, 'partner').then(setPartners).catch(() => {})
 }

 useEffect(() => {
  loadGames()
  loadTournaments()
 }, [gameStatus, gameFromDate, gameToDate])

 const handleGrantCredits = async (e) => {
  e.preventDefault()
  setError('')
  setSuccess('')
  setGranting(true)
  try {
   const payload = {
    email: grantEmail,
    amount: parseInt(grantAmount, 10),
    reason: grantReason.trim() || undefined,
   }
   if (walletAction === 'debit') {
    await adminDebitCredits(token, payload)
   } else {
    await adminGrantCredits(token, payload)
   }
   setSuccess(
    walletAction === 'debit'
      ?
      t('admin.debitSuccess', { amount: grantAmount, email: grantEmail })
     : t('admin.grantSuccess', { amount: grantAmount, email: grantEmail })
   )
   setGrantEmail('')
   setGrantAmount('')
   setGrantReason('')
   setEmailSearch('')
   refreshWalletData()
  } catch (err) {
   setError(err.message || (walletAction === 'debit' ? t('admin.debitFailed') : t('admin.grantFailed')))
  } finally {
   setGranting(false)
  }
 }

 const handleStatusChange = async (eventId, newStatus) => {
  try {
   await updateEvent(token, eventId, { status: newStatus })
   loadGames()
   loadTournaments()
   setSuccess(`${t('admin.gameStatusUpdated')}: ${t(`admin.${newStatus}`)}`)
  } catch (err) {
   setError(err.message)
  }
 }

 const handleRevokeGrant = async (tx) => {
  setError('')
  setSuccess('')
  setRevokingTransactionId(tx.id)
  try {
   await adminRevokeGrant(token, tx.id)
   setSuccess(t('admin.grantRevokedSuccess', { amount: tx.amount, email: tx.user_email }))
   loadData()
  } catch (err) {
   setError(err.message || t('admin.grantRevokeFailed'))
  } finally {
   setRevokingTransactionId('')
  }
 }

 const handlePlayerRoleChange = async (targetUser, nextValue) => {
  const nextIsAdmin = nextValue === 'admin'
  setError('')
  setSuccess('')
  setUpdatingUserId(targetUser.id)
  try {
   await adminSetUserAdminRole(token, targetUser.id, nextIsAdmin)
   setPlayers((current) => current.map((entry) => (
    entry.id === targetUser.id ? { ...entry, is_admin: nextIsAdmin } : entry
   )))
   setSuccess(nextIsAdmin ? t('admin.adminGranted') : t('admin.adminRevoked'))
  } catch (err) {
   setError(err.message || t('admin.roleUpdateFailed'))
  } finally {
   setUpdatingUserId('')
  }
 }

 const formatDate = (dateStr) => {
  return new Date(dateStr).toLocaleString(i18n.language === 'ru' ? 'ru-RU' : 'en-US', {
   month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
  })
 }

 const adminTabs = ['wallet', 'players', 'partners', 'games', 'tournaments', 'venues']

 // Email autocomplete filtering
 const allUsers = [...players, ...partners]
 const suggestions = emailSearch.length > 0
  ?
   allUsers.filter(u => u.email.toLowerCase().includes(emailSearch.toLowerCase())).slice(0, 5)
  : []

 const selectedWalletUser = allUsers.find((u) => u.email.toLowerCase() === grantEmail.toLowerCase())

 const updateTournamentForm = (key, value) => {
  setTournamentForm((current) => ({ ...current, [key]: value }))
 }

 const handleCreateTournament = async (e) => {
  e.preventDefault()
  setError('')
  setSuccess('')
  setCreatingTournament(true)
  try {
   const payload = {
    title: tournamentForm.title,
    sport_id: tournamentForm.sport_id,
    venue_id: tournamentForm.venue_id,
    start_at: toIsoOrNull(tournamentForm.start_at),
    end_at: toIsoOrNull(tournamentForm.end_at),
    registration_deadline: toIsoOrNull(tournamentForm.registration_deadline),
    teams_count: parseInt(tournamentForm.teams_count, 10),
    entry_fee_credits_team: parseInt(tournamentForm.entry_fee_credits_team, 10),
    description: tournamentForm.description.trim() || undefined,
    is_featured: Boolean(tournamentForm.is_featured),
   }
   await adminCreateTournament(token, payload)
   setTournamentForm({
    title: '',
    sport_id: '',
    venue_id: '',
    start_at: '',
    end_at: '',
    registration_deadline: '',
    teams_count: '8',
    entry_fee_credits_team: '',
    description: '',
    is_featured: true,
   })
   await loadTournaments()
   setSuccess(t('admin.tournamentCreated'))
  } catch (err) {
   setError(err.message || t('admin.tournamentCreateFailed'))
  } finally {
   setCreatingTournament(false)
  }
 }

 const handleTournamentRegistrationToggle = async (eventItem, nextClosedValue) => {
  setError('')
  setSuccess('')
  setTogglingRegistrationEventId(eventItem.id)
  try {
   await updateEvent(token, eventItem.id, { registration_closed: nextClosedValue })
   await loadTournaments()
   setSuccess(nextClosedValue ? t('admin.registrationClosed') : t('admin.registrationOpened'))
  } catch (err) {
   setError(err.message || t('admin.tournamentUpdateFailed'))
  } finally {
   setTogglingRegistrationEventId('')
  }
 }

 const handleTournamentRegistrationDelete = async (eventId, registration) => {
  setError('')
  setSuccess('')
  setRemovingTournamentRegistrationId(registration.id)
  try {
   await adminDeleteTournamentRegistration(token, eventId, registration.id)
   await loadTournaments()
   setSuccess(t('admin.teamRemoved'))
  } catch (err) {
   setError(err.message || t('admin.teamRemoveFailed'))
  } finally {
   setRemovingTournamentRegistrationId('')
  }
 }

 const handleTournamentRegistrationSloganChange = (registrationId, value) => {
  setRegistrationSlogans((current) => ({ ...current, [registrationId]: value }))
 }

 const handleTournamentRegistrationSave = async (eventId, registrationId) => {
  setError('')
  setSuccess('')
  setSavingTournamentRegistrationId(registrationId)
  try {
   await adminUpdateTournamentRegistration(token, eventId, registrationId, {
    team_slogan: (registrationSlogans[registrationId] || '').trim() || null,
   })
   await loadTournaments()
   setSuccess(t('admin.teamSloganSaved'))
  } catch (err) {
   setError(err.message || t('admin.teamSloganSaveFailed'))
  } finally {
   setSavingTournamentRegistrationId('')
  }
 }

 const updatePartnerForm = (key, value) => {
  if (key === 'email') {
   setPartnerCodeSent(false)
  }
  setPartnerForm((current) => ({ ...current, [key]: value }))
 }

 const handleSendPartnerCode = async () => {
  setError('')
  setSuccess('')
  if (!partnerForm.email.trim()) {
   setError(t('auth.enterEmailFirst'))
   return
  }

  setSendingPartnerCode(true)
  try {
   const res = await sendVerificationCode({ email: partnerForm.email })
   setSuccess(res.detail || t('auth.codeSent'))
   setPartnerCodeSent(true)
  } catch (err) {
   setError(err.message || t('admin.partnerCreateFailed'))
  } finally {
   setSendingPartnerCode(false)
  }
 }

 const handleCreatePartner = async (e) => {
  e.preventDefault()
  setError('')
  setSuccess('')
  setCreatingPartner(true)
  try {
   await adminCreatePartner(token, partnerForm)
   setSuccess(`${t('admin.partnerCreated')} ${partnerForm.email}`)
   setPartnerForm({
    first_name: '',
    last_name: '',
    birth_date: '',
    email: '',
    verification_code: '',
    password: '',
   })
   setPartnerCodeSent(false)
   adminGetUsersWithBalance(token, 'partner').then(setPartners).catch(() => {})
  } catch (err) {
   setError(err.message || t('admin.partnerCreateFailed'))
  } finally {
   setCreatingPartner(false)
  }
 }

 return (
  <div className="dashboard-page admin-page">
   {/* Stats Grid */}
   <div className="stats-grid admin-stats-grid">
    <div className="stat-card glass-card"><div className="stat-card-icon">👥</div><div className="stat-card-value">{players.length}</div><div className="stat-card-label">{t('admin.totalPlayers')}</div></div>
    <div className="stat-card glass-card"><div className="stat-card-icon">🏢</div><div className="stat-card-value">{partners.length}</div><div className="stat-card-label">{t('admin.partnersLabel')}</div></div>
    <div className="stat-card glass-card"><div className="stat-card-icon">🏟️</div><div className="stat-card-value">{venues.length}</div><div className="stat-card-label">{t('admin.venuesLabel')}</div></div>
    <div className="stat-card glass-card"><div className="stat-card-icon">🎮</div><div className="stat-card-value">{events.length + tournaments.length}</div><div className="stat-card-label">{t('admin.gamesLabel')}</div></div>
   </div>
   <div className="glass-card admin-summary-strip" aria-label={t('admin.walletControl')}>
    <span>{players.length} {t('admin.totalPlayers').toLowerCase()}</span>
    <span className="admin-summary-separator" aria-hidden="true">•</span>
    <span>{partners.length} {t('admin.partnersLabel').toLowerCase()}</span>
    <span className="admin-summary-separator" aria-hidden="true">•</span>
    <span>{venues.length} {t('admin.venuesLabel').toLowerCase()}</span>
    <span className="admin-summary-separator" aria-hidden="true">•</span>
    <span>{events.length + tournaments.length} {t('admin.gamesLabel').toLowerCase()}</span>
   </div>

   {/* Tabs */}
   <div className="admin-tabs">
    {adminTabs.map(tabKey => (
     <button key={tabKey} className={`admin-tab ${tab === tabKey ? 'active' : ''}`} onClick={() => setTab(tabKey)}>
      {tabKey === 'wallet' && t('admin.walletTab')}
      {tabKey === 'players' && t('admin.playersTab')}
      {tabKey === 'partners' && t('admin.partnersTab')}
      {tabKey === 'games' && t('admin.gamesTab')}
      {tabKey === 'tournaments' && t('admin.tournamentsTab')}
      {tabKey === 'venues' && t('admin.venuesTab')}
     </button>
    ))}
   </div>

   {error && <div className="alert alert-error">{error}</div>}
   {success && <div className="alert alert-success">{success}</div>}

   {/* Wallet Control Tab */}
   {tab === 'wallet' && (
    <div className="admin-wallet-layout">
     <div className="dashboard-card glass-card admin-wallet-card">
      <h3>{t('admin.walletAdjustments')}</h3>
      <form onSubmit={handleGrantCredits} className="grant-form">
       <div className="form-group">
        <label>{t('admin.walletAction')}</label>
        <select
         value={walletAction}
         onChange={(e) => setWalletAction(e.target.value)}
         className="filter-select"
        >
         <option value="grant">{t('admin.grantBtn')}</option>
         <option value="debit">{t('admin.debitBtn')}</option>
        </select>
       </div>
       <div className="form-group" style={{ position: 'relative' }}>
        <label>{t('admin.userEmail')}</label>
        <input
         type="text"
         placeholder={t('admin.emailPlaceholder')}
         value={emailSearch || grantEmail}
         onChange={(e) => {
          setEmailSearch(e.target.value)
          setGrantEmail(e.target.value)
          setShowSuggestions(true)
         }}
         onFocus={() => setShowSuggestions(true)}
         onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
         required
        />
        {showSuggestions && suggestions.length > 0 && (
         <div className="autocomplete-dropdown">
          {suggestions.map(u => (
           <div
            key={u.id}
            className="autocomplete-item"
            onMouseDown={() => {
             setGrantEmail(u.email)
             setEmailSearch(u.email)
             setShowSuggestions(false)
            }}
           >
            <UserAvatar user={u} alt="" className="user-avatar-small" />
            <div>
             <div>{u.email}</div>
             <small style={{ opacity: 0.6 }}>{u.balance} {t('dashboard.credits').toLowerCase()}</small>
            </div>
           </div>
          ))}
         </div>
        )}
       </div>
       {selectedWalletUser && (
        <div className="form-group">
         <label>{t('admin.currentCredits')}</label>
         <div className="credits-badge-inline">{selectedWalletUser.balance} cr</div>
        </div>
       )}
       <div className="form-group">
        <label>{t('admin.amount')}</label>
        <input
         type="number"
         placeholder="500"
         value={grantAmount}
         onChange={(e) => setGrantAmount(e.target.value)}
         min="1"
         required
        />
       </div>
       <div className="form-group">
        <label>{t('wallet.reason')}</label>
        <input
         type="text"
         placeholder={t('wallet.reasonPlaceholder')}
         value={grantReason}
         onChange={(e) => setGrantReason(e.target.value)}
        />
       </div>
       <button type="submit" className="btn-primary" disabled={granting}>
        {granting ? t('admin.walletUpdating') : walletAction === 'debit' ? t('admin.debitBtn') : t('admin.grantBtn')}
       </button>
      </form>
     </div>

     <div className="dashboard-card glass-card admin-wallet-card admin-wallet-history-card">
      <h3>{t('admin.creditHistory')}</h3>
      <div className="transactions-list">
       {transactions.length === 0 ? (
        <p className="empty-text">{t('admin.noTransactions')}</p>
       ) : (
        transactions.map((tx) => (
         <div key={tx.id} className="transaction-item">
          <div className={`tx-type ${tx.tx_type}`}>
           {tx.tx_type === 'grant' && '💰'}
           {tx.tx_type === 'refund' && '↩️'}
           {tx.tx_type === 'spend' && '💸'}
           {tx.tx_type === 'admin_debit' && '➖'}
           {tx.tx_type === 'grant_reversal' && '⛔'}
          </div>
          <div className="tx-details">
           <div className="tx-user">{tx.user_email}</div>
           <div className="tx-time">{t(`wallet.txType.${tx.tx_type}`, { defaultValue: tx.tx_type })}</div>
           <div className="tx-time">{formatDate(tx.created_at)}</div>
           {tx.reason && <div className="tx-time">{tx.reason}</div>}
           {tx.is_revoked && <div className="tx-time">{t('admin.grantRevokedLabel')}</div>}
          </div>
          <div className={`tx-amount ${tx.tx_type}`}>
           {tx.tx_type === 'spend' || tx.tx_type === 'grant_reversal' || tx.tx_type === 'admin_debit' ? '-' : '+'}{tx.amount} cr
          </div>
          {tx.can_revoke && (
           <button
            type="button"
            className="btn-secondary"
            onClick={() => handleRevokeGrant(tx)}
            disabled={revokingTransactionId === tx.id}
           >
            {revokingTransactionId === tx.id ? t('admin.revokingGrant') : t('admin.revokeGrant')}
           </button>
          )}
         </div>
        ))
       )}
      </div>
     </div>
    </div>
   )}

   {/* Players Tab - with credits */}
   {tab === 'players' && (
    <div className="dashboard-card glass-card">
     <h3>{t('admin.allPlayers')} ({players.length})</h3>
     <div className="admin-players-mobile-list">
      {players.length === 0 ? (
       <p className="empty-text">{t('admin.noPlayers')}</p>
      ) : (
       players.map((u) => (
        <div key={`mobile-${u.id}`} className="glass-card admin-user-mobile-card">
         <div className="admin-user-mobile-head">
          <div className="user-cell admin-player-cell">
           <UserAvatar user={u} alt="" className="user-avatar-small" />
           <div className="admin-user-mobile-copy">
            <span className="admin-player-name">{getUserDisplayName(u)}</span>
            <span className="admin-player-email">{u.email}</span>
           </div>
          </div>
          <span className="credits-badge-inline compact-credits-badge">{u.balance} cr</span>
         </div>
         <div className="admin-user-mobile-meta">
          <div className="admin-user-mobile-row">
           <span>{t('admin.roleCol')}</span>
           <select
            value={u.is_admin ? 'admin' : 'player'}
            onChange={(e) => handlePlayerRoleChange(u, e.target.value)}
            disabled={updatingUserId === u.id || user.id === u.id}
            className="filter-select compact-role-select"
           >
            <option value="player">{t('role.player')}</option>
            <option value="admin">{t('role.admin')}</option>
           </select>
          </div>
          <div className="admin-user-mobile-row">
           <span>{t('admin.gamesCol')}</span>
           <strong>{u.games_played}</strong>
          </div>
         </div>
        </div>
       ))
      )}
     </div>
     <div className="admin-table admin-players-table">
      {players.length === 0 ? (
       <p className="empty-text">{t('admin.noPlayers')}</p>
      ) : (
       <table>
        <thead>
         <tr>
          <th>{t('admin.user')}</th>
          <th>{t('admin.emailCol')}</th>
          <th>{t('admin.roleCol')}</th>
          <th>{t('admin.creditsCol')}</th>
          <th>{t('admin.gamesCol')}</th>
         </tr>
        </thead>
        <tbody>
         {players.map((u) => (
          <tr key={u.id}>
           <td>
            <div className="user-cell admin-player-cell">
             <UserAvatar user={u} alt="" className="user-avatar-small" />
             <span className="admin-player-name">{getUserDisplayName(u)}</span>
            </div>
           </td>
           <td className="admin-player-email">{u.email}</td>
           <td>
            <select
             value={u.is_admin ? 'admin' : 'player'}
             onChange={(e) => handlePlayerRoleChange(u, e.target.value)}
             disabled={updatingUserId === u.id || user.id === u.id}
             className="filter-select compact-role-select"
            >
             <option value="player">{t('role.player')}</option>
             <option value="admin">{t('role.admin')}</option>
            </select>
           </td>
           <td><span className="credits-badge-inline compact-credits-badge">{u.balance} cr</span></td>
           <td>{u.games_played}</td>
          </tr>
         ))}
        </tbody>
       </table>
      )}
     </div>
    </div>
   )}

   {/* Partners Tab */}
   {tab === 'partners' && (
    <div className="admin-partners-layout">
     <div className="dashboard-card glass-card">
      <h3>{t('admin.allPartners')} ({partners.length})</h3>
      <div className="admin-table admin-partners-table">
       {partners.length === 0 ? (
        <p className="empty-text">{t('admin.noPartners')}</p>
       ) : (
        <table>
         <thead>
          <tr>
           <th>{t('admin.user')}</th>
           <th>{t('admin.emailCol')}</th>
           <th>{t('admin.creditsCol')}</th>
           <th>{t('admin.bio')}</th>
          </tr>
         </thead>
         <tbody>
          {partners.map((u) => (
           <tr key={u.id}>
            <td>
             <div className="user-cell admin-player-cell">
              <UserAvatar user={u} alt="" className="user-avatar-small" />
              <span className="admin-player-name">{getUserDisplayName(u)}</span>
             </div>
            </td>
            <td className="admin-player-email">{u.email}</td>
            <td><span className="credits-badge-inline compact-credits-badge">{u.balance} cr</span></td>
            <td className="partner-bio-cell">{u.bio || '-'}</td>
           </tr>
          ))}
         </tbody>
        </table>
       )}
      </div>
     </div>

     <div className="dashboard-card glass-card">
      <h3>{t('admin.createPartner')}</h3>
      <form onSubmit={handleCreatePartner} className="grant-form">
       <div className="auth-name-grid">
        <div className="form-group">
         <label>{t('auth.firstName')}</label>
         <input
          type="text"
          value={partnerForm.first_name}
          onChange={(e) => updatePartnerForm('first_name', e.target.value)}
          required
         />
        </div>
        <div className="form-group">
         <label>{t('auth.lastName')}</label>
         <input
          type="text"
          value={partnerForm.last_name}
          onChange={(e) => updatePartnerForm('last_name', e.target.value)}
          required
         />
        </div>
       </div>
       <div className="form-group">
        <label>{t('auth.birthDate')}</label>
        <input
         type="date"
         value={partnerForm.birth_date}
         onChange={(e) => updatePartnerForm('birth_date', e.target.value)}
         required
        />
       </div>
       <div className="form-group">
        <label>{t('admin.partnerEmail')}</label>
        <div className="admin-inline-form-row">
         <input
          className="admin-partner-email-input"
          type="email"
          value={partnerForm.email}
          onChange={(e) => updatePartnerForm('email', e.target.value)}
          placeholder={t('auth.emailPlaceholder')}
          required
         />
         <button
          type="button"
          className="btn-secondary"
          onClick={handleSendPartnerCode}
          disabled={sendingPartnerCode}
         >
          {sendingPartnerCode ? t('auth.sending') : t('auth.sendCode')}
         </button>
        </div>
        {partnerCodeSent && (
         <small style={{ display: 'block', marginTop: '0.5rem', opacity: 0.75 }}>
          {t('auth.codeSentHint')}
         </small>
        )}
       </div>
       <div className="form-group">
        <label>{t('auth.verificationCode')}</label>
        <input
         type="text"
         value={partnerForm.verification_code}
         onChange={(e) => updatePartnerForm('verification_code', e.target.value)}
         placeholder={t('auth.codePlaceholder')}
         required
        />
       </div>
       <div className="form-group">
        <label>{t('admin.partnerPassword')}</label>
        <input
         type="password"
         value={partnerForm.password}
         onChange={(e) => updatePartnerForm('password', e.target.value)}
         placeholder={t('auth.passwordCreatePlaceholder')}
         minLength={8}
         required
        />
       </div>
       <button type="submit" className="btn-primary" disabled={creatingPartner}>
        {creatingPartner ? t('admin.creatingPartner') : t('admin.createPartnerBtn')}
       </button>
      </form>
     </div>
    </div>
   )}

   {/* Games Tab - with filters and edit */}
   {tab === 'games' && (
    <div className="dashboard-card glass-card">
     <h3>{t('admin.allGames')} ({events.length})</h3>
     <div className="games-filter-bar">
      <select value={gameStatus} onChange={e => setGameStatus(e.target.value)} className="filter-select">
       <option value="">{t('admin.allStatuses')}</option>
       <option value="active">{t('admin.active')}</option>
       <option value="completed">{t('admin.completed')}</option>
       <option value="cancelled">{t('admin.cancelled')}</option>
      </select>
      <input type="date" value={gameFromDate} onChange={e => setGameFromDate(e.target.value)} className="filter-input" />
      <input type="date" value={gameToDate} onChange={e => setGameToDate(e.target.value)} className="filter-input" />
     </div>
     <div className="admin-games-mobile-list">
      {events.length === 0 ? (
       <p className="empty-text">{t('admin.noGames')}</p>
      ) : (
       events.map((e) => (
        <div key={`mobile-game-${e.id}`} className="glass-card admin-data-mobile-card">
         <div className="admin-data-mobile-head">
          <strong>{e.venue_name || t('common.venue')}</strong>
          <span className={`status-badge ${e.status}`}>{t(`admin.${e.status}`)}</span>
         </div>
         <div className="admin-data-mobile-stack">
          <div className="admin-data-mobile-row">
           <span>{t('admin.sportCol')}</span>
           <strong>{e.sport_name || '-'}</strong>
          </div>
          <div className="admin-data-mobile-row">
           <span>{t('admin.date')}</span>
           <strong>{formatDate(e.start_at)}</strong>
          </div>
          <div className="admin-data-mobile-row">
           <span>{t('admin.playersCol')}</span>
           <strong>{e.current_players}/{e.required_players}</strong>
          </div>
          <div className="admin-data-mobile-row">
           <span>{i18n.language === 'ru' ? 'Аренда' : 'Rent'}</span>
           <strong>{e.admin_rent_total}</strong>
          </div>
          <div className="admin-data-mobile-row">
           <span>{i18n.language === 'ru' ? 'Комиссия' : 'Commission'}</span>
           <strong>{e.admin_platform_fee_total}</strong>
          </div>
          <div className="admin-data-mobile-row admin-data-mobile-row-control">
           <span>{t('admin.actions')}</span>
           <select value={e.status} onChange={(ev) => handleStatusChange(e.id, ev.target.value)} className="status-select">
            <option value="active">{t('admin.active')}</option>
            <option value="completed">{t('admin.completed')}</option>
            <option value="cancelled">{t('admin.cancelled')}</option>
           </select>
          </div>
         </div>
        </div>
       ))
      )}
     </div>
     <div className="admin-table admin-games-table">
      {events.length === 0 ? (
       <p className="empty-text">{t('admin.noGames')}</p>
      ) : (
       <table>
        <thead>
         <tr>
          <th>{t('admin.game')}</th>
          <th>{t('admin.sportCol')}</th>
          <th>{t('admin.date')}</th>
          <th>{t('admin.playersCol')}</th>
          <th>{i18n.language === 'ru' ? 'Аренда' : 'Rent'}</th>
          <th>{i18n.language === 'ru' ? 'Комиссия' : 'Commission'}</th>
          <th>{t('admin.status')}</th>
          <th>{t('admin.actions')}</th>
         </tr>
        </thead>
        <tbody>
         {events.map((e) => (
          <tr key={e.id}>
           <td>{e.venue_name || t('common.venue')}</td>
           <td>{e.sport_name || '-'}</td>
           <td>{formatDate(e.start_at)}</td>
           <td>{e.current_players}/{e.required_players}</td>
           <td>{e.admin_rent_total}</td>
           <td>{e.admin_platform_fee_total}</td>
           <td><span className={`status-badge ${e.status}`}>{t(`admin.${e.status}`)}</span></td>
           <td>
            <select value={e.status} onChange={(ev) => handleStatusChange(e.id, ev.target.value)} className="status-select">
             <option value="active">{t('admin.active')}</option>
             <option value="completed">{t('admin.completed')}</option>
             <option value="cancelled">{t('admin.cancelled')}</option>
            </select>
           </td>
          </tr>
         ))}
        </tbody>
       </table>
      )}
     </div>
    </div>
   )}

   {tab === 'tournaments' && (
    <div className="admin-tournaments-layout">
     <div className="dashboard-card glass-card">
      <h3>{t('admin.createTournament')}</h3>
      <form onSubmit={handleCreateTournament} className="grant-form">
       <div className="form-group">
        <label>{t('admin.tournamentTitle')}</label>
        <input
         type="text"
         value={tournamentForm.title}
         onChange={(e) => updateTournamentForm('title', e.target.value)}
         placeholder={t('admin.tournamentTitlePlaceholder')}
         required
        />
       </div>
       <div className="admin-tournament-form-grid">
        <div className="form-group">
         <label>{t('admin.sportCol')}</label>
         <select
          value={tournamentForm.sport_id}
          onChange={(e) => updateTournamentForm('sport_id', e.target.value)}
          className="filter-select"
          required
         >
          <option value="">{t('admin.selectSport')}</option>
          {sports.map((sport) => (
           <option key={sport.id} value={sport.id}>{sport.name}</option>
          ))}
         </select>
        </div>
        <div className="form-group">
         <label>{t('admin.venueCol')}</label>
         <select
          value={tournamentForm.venue_id}
          onChange={(e) => updateTournamentForm('venue_id', e.target.value)}
          className="filter-select"
          required
         >
          <option value="">{t('admin.selectVenue')}</option>
          {venues.map((venue) => (
           <option key={venue.id} value={venue.id}>{venue.name}</option>
          ))}
         </select>
        </div>
        <div className="form-group">
         <label>{t('admin.startAt')}</label>
         <input
          type="datetime-local"
          value={tournamentForm.start_at}
          onChange={(e) => updateTournamentForm('start_at', e.target.value)}
          required
         />
        </div>
        <div className="form-group">
         <label>{t('admin.endAt')}</label>
         <input
          type="datetime-local"
          value={tournamentForm.end_at}
          onChange={(e) => updateTournamentForm('end_at', e.target.value)}
          required
         />
        </div>
        <div className="form-group">
         <label>{t('admin.registrationDeadline')}</label>
         <input
          type="datetime-local"
          value={tournamentForm.registration_deadline}
          onChange={(e) => updateTournamentForm('registration_deadline', e.target.value)}
          required
         />
        </div>
        <div className="form-group">
         <label>{t('admin.teamCount')}</label>
         <input
          type="number"
          min="2"
          max="64"
          value={tournamentForm.teams_count}
          onChange={(e) => updateTournamentForm('teams_count', e.target.value)}
          required
         />
        </div>
        <div className="form-group">
         <label>{t('admin.entryFeePerTeam')}</label>
         <input
          type="number"
          min="1"
          value={tournamentForm.entry_fee_credits_team}
          onChange={(e) => updateTournamentForm('entry_fee_credits_team', e.target.value)}
          placeholder="1500"
          required
         />
        </div>
       </div>
       <div className="form-group">
        <label>{t('admin.tournamentDescription')}</label>
        <textarea
         value={tournamentForm.description}
         onChange={(e) => updateTournamentForm('description', e.target.value)}
         placeholder={t('admin.tournamentDescriptionPlaceholder')}
         rows={4}
        />
       </div>
       <label className="checkbox admin-checkbox-row">
        <input
         type="checkbox"
         checked={Boolean(tournamentForm.is_featured)}
         onChange={(e) => updateTournamentForm('is_featured', e.target.checked)}
        />
        <span>{t('admin.highlightTournament')}</span>
       </label>
       <button type="submit" className="btn-primary" disabled={creatingTournament}>
        {creatingTournament ? t('admin.creatingTournament') : t('admin.createTournamentBtn')}
       </button>
      </form>
     </div>

     <div className="dashboard-card glass-card">
      <div className="admin-tournaments-header">
       <div>
        <h3>{t('admin.allTournaments')} ({tournaments.length})</h3>
        <p className="page-subtitle">{t('admin.tournamentsHint')}</p>
       </div>
       {loadingTournamentRegistrations ? (
        <span className="compact-credits-badge">{t('admin.loadingTeams')}</span>
       ) : null}
      </div>
      {tournaments.length === 0 ? (
       <p className="empty-text">{t('admin.noTournaments')}</p>
      ) : (
       <div className="admin-tournaments-list">
        {tournaments.map((eventItem) => {
         const registrations = tournamentRegistrations[eventItem.id] || []
         const isLockedByCapacityOrDeadline = (
          registrations.length >= eventItem.teams_count ||
          new Date(eventItem.registration_deadline).getTime() <= Date.now()
         )
         const isAutoClosed = eventItem.registration_is_closed && !eventItem.registration_closed
         return (
          <div key={eventItem.id} className="glass-card admin-tournament-card">
           <div className="admin-tournament-card-top">
            <div>
             <div className="admin-tournament-title-row">
              <h4>{eventItem.title}</h4>
              {eventItem.is_featured ? <span className="admin-inline-badge">{t('admin.featured')}</span> : null}
             </div>
             <p className="admin-tournament-meta">
              {eventItem.sport_name || '-'} • {eventItem.venue_name || t('common.venue')}
             </p>
            </div>
            <div className="admin-tournament-statuses">
             <span className={`status-badge ${eventItem.status}`}>{t(`admin.${eventItem.status}`)}</span>
             <span className={`status-badge ${eventItem.registration_is_closed ? 'registration-closed' : 'registration-open'}`}>
              {eventItem.registration_is_closed ? t('admin.registrationClosedBadge') : t('admin.registrationOpenBadge')}
             </span>
            </div>
           </div>

           <div className="admin-tournament-metrics">
            <div>
             <span>{t('admin.date')}</span>
             <strong>{formatDate(eventItem.start_at)}</strong>
            </div>
            <div>
             <span>{t('admin.registrationDeadline')}</span>
             <strong>{formatDate(eventItem.registration_deadline)}</strong>
            </div>
            <div>
             <span>{t('admin.teamCount')}</span>
             <strong>{registrations.length}/{eventItem.teams_count}</strong>
            </div>
            <div>
             <span>{t('admin.entryFeePerTeam')}</span>
             <strong>{eventItem.entry_fee_credits_team} cr</strong>
            </div>
           </div>

           <div className="admin-tournament-actions">
            <button
             type="button"
             className="btn-secondary"
             disabled={togglingRegistrationEventId === eventItem.id || isLockedByCapacityOrDeadline}
             onClick={() => handleTournamentRegistrationToggle(eventItem, !eventItem.registration_closed)}
            >
             {eventItem.registration_closed ? t('admin.openRegistration') : t('admin.closeRegistration')}
            </button>
             {isLockedByCapacityOrDeadline ? (
              <span className="admin-muted-note">{t('admin.registrationAutoClosed')}</span>
             ) : null}
           </div>

            {eventItem.description ? (
             <p className="admin-tournament-description">{eventItem.description}</p>
            ) : null}

           <div className="admin-team-list">
            {registrations.length === 0 ? (
             <p className="empty-text">{t('admin.noTournamentTeams')}</p>
            ) : (
             registrations.map((registration) => (
              <div key={registration.id} className="admin-team-card">
               <div className="admin-team-card-head">
                <div>
                 <strong>{registration.team_name}</strong>
                 <p>{registration.captain_name} • {registration.captain_phone}</p>
                </div>
                <button
                 type="button"
                 className="btn-secondary admin-danger-btn"
                 disabled={removingTournamentRegistrationId === registration.id}
                 onClick={() => handleTournamentRegistrationDelete(eventItem.id, registration)}
                >
                 {removingTournamentRegistrationId === registration.id ? t('admin.removingTeam') : t('admin.removeTeam')}
                </button>
               </div>
               <div className="admin-team-slogan-editor">
                <label>{t('admin.teamSlogan')}</label>
                <div className="admin-team-slogan-row">
                 <input
                  type="text"
                  value={registrationSlogans[registration.id] ?? registration.team_slogan ?? ''}
                  onChange={(e) => handleTournamentRegistrationSloganChange(registration.id, e.target.value)}
                  placeholder={t('admin.teamSloganPlaceholder')}
                 />
                 <button
                  type="button"
                  className="btn-secondary"
                  disabled={savingTournamentRegistrationId === registration.id}
                  onClick={() => handleTournamentRegistrationSave(eventItem.id, registration.id)}
                 >
                  {savingTournamentRegistrationId === registration.id ? t('admin.savingTeamSlogan') : t('admin.saveTeamSlogan')}
                 </button>
                </div>
               </div>
               <div className="admin-team-members">
                {registration.members.map((member) => (
                 <span key={member.id} className={`admin-team-member-chip ${member.is_captain ? 'captain' : ''}`}>
                  {member.first_name} {member.last_name}{member.is_captain ? ` • ${t('admin.captainLabel')}` : ''}
                 </span>
                ))}
               </div>
              </div>
             ))
            )}
           </div>
          </div>
         )
        })}
       </div>
      )}
     </div>
    </div>
   )}

   {/* Venues Tab */}
   {tab === 'venues' && (
    <div className="dashboard-card glass-card">
     <h3>{t('admin.allVenues')} ({venues.length})</h3>
     <div className="admin-venues-mobile-list">
      {venues.length === 0 ? (
       <p className="empty-text">{t('admin.noVenues')}</p>
      ) : (
       venues.map((v) => (
        <div key={`mobile-venue-${v.id}`} className="glass-card admin-data-mobile-card">
         <div className="admin-data-mobile-head">
          <strong>{v.name}</strong>
          <span className="rate-cell">{v.hourly_rate} cr/hr</span>
         </div>
         <div className="admin-data-mobile-stack">
          <div className="admin-data-mobile-row">
           <span>{t('admin.partnerEmailCol')}</span>
           <strong>{v.partner_email || '-'}</strong>
          </div>
          <div className="admin-data-mobile-row">
           <span>{t('admin.cityCol')}</span>
           <strong>{v.city}</strong>
          </div>
          <div className="admin-data-mobile-row">
           <span>{t('admin.addressCol')}</span>
           <strong>{v.address}</strong>
          </div>
         </div>
        </div>
       ))
      )}
     </div>
     <div className="admin-table admin-venues-table">
      {venues.length === 0 ? (
       <p className="empty-text">{t('admin.noVenues')}</p>
      ) : (
       <table>
        <thead>
         <tr>
          <th>{t('admin.venueCol')}</th>
          <th>{t('admin.partnerEmailCol')}</th>
          <th>{t('admin.cityCol')}</th>
          <th>{t('admin.addressCol')}</th>
          <th>{t('admin.rateCol')}</th>
         </tr>
        </thead>
        <tbody>
         {venues.map((v) => (
          <tr key={v.id}>
           <td><div className="venue-cell"><span className="venue-icon">🏟️</span><span>{v.name}</span></div></td>
           <td>{v.partner_email || '-'}</td>
           <td>{v.city}</td>
           <td>{v.address}</td>
           <td className="rate-cell">{v.hourly_rate} cr/hr</td>
          </tr>
         ))}
        </tbody>
       </table>
      )}
     </div>
    </div>
   )}
  </div>
 )
}
