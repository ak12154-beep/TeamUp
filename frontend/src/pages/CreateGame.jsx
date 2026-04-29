import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { getVenueSlots } from '../api/availability'
import { createEvent } from '../api/events'
import { getSports } from '../api/sports'
import { getVenues } from '../api/venues'
import '../styles/CreateGame.css'
import { createDemoEvent, getDemoSports, getDemoVenueSlots, getDemoVenues, isDemoToken } from '../demo/demoData'

const HOUR_MS = 60 * 60 * 1000
const REQUIRED_PLAYERS_RULES = {
 football: [10, 15, 20],
 basketball: [10, 15, 20],
 volleyball: [12, 18, 24],
}

const INITIAL_FORM = {
 sport_id: '',
 venue_id: '',
 selectedDate: '',
 selectedHour: '',
 duration_hours: 1,
 required_players: 10,
 teams_count: 2,
}

function getDateKey(date) {
 const year = date.getFullYear()
 const month = String(date.getMonth() + 1).padStart(2, '0')
 const day = String(date.getDate()).padStart(2, '0')
 return `${year}-${month}-${day}`
}

function getSportLabel(name, t) {
 if (!name) return t('common.game')
 const normalized = name.toLowerCase()
 if (normalized.includes('football') || normalized.includes('soccer')) return t('welcome.football')
 if (normalized.includes('basketball')) return t('welcome.basketball')
 if (normalized.includes('volleyball')) return t('welcome.volleyball')
 if (normalized.includes('tennis')) return t('games.tennis')
 if (normalized.includes('padel')) return t('games.padel')
 return name
}

function getSportRuleKey(name) {
 const normalized = name.toLowerCase() || ''
 if (normalized.includes('football') || normalized.includes('soccer')) return 'football'
 if (normalized.includes('basketball')) return 'basketball'
 if (normalized.includes('volleyball')) return 'volleyball'
 return null
}

export default function CreateGame({ token }) {
 const navigate = useNavigate()
 const { t, i18n } = useTranslation()
 const [sports, setSports] = useState([])
 const [venues, setVenues] = useState([])
 const [slots, setSlots] = useState([])
 const [error, setError] = useState('')
 const [showWalletPrompt, setShowWalletPrompt] = useState(false)
 const [submitting, setSubmitting] = useState(false)
 const [loadingSlots, setLoadingSlots] = useState(false)
 const [form, setForm] = useState(INITIAL_FORM)

 useEffect(() => {
  if (isDemoToken(token)) {
   setSports(getDemoSports())
   setVenues(getDemoVenues())
   return
  }
  getSports().then(setSports)
  getVenues().then(setVenues)
 }, [])

 useEffect(() => {
  if (!form.venue_id) {
   setSlots([])
   return
  }

  setLoadingSlots(true)
  setSlots([])
  const from = new Date()
  const to = new Date(Date.now() + 30 * 86400000)

  if (isDemoToken(token)) {
   setSlots(getDemoVenueSlots(form.venue_id))
   setLoadingSlots(false)
   return
  }

  getVenueSlots(form.venue_id, from.toISOString(), to.toISOString())
   .then((list) => {
    const openSlots = list
     .filter((slot) => slot.status === 'open')
     .sort((a, b) => new Date(a.start_at) - new Date(b.start_at))
    setSlots(openSlots)
   })
   .catch(() => setSlots([]))
   .finally(() => setLoadingSlots(false))
 }, [form.venue_id])

 const selectedVenue = useMemo(
  () => venues.find((venue) => String(venue.id) === String(form.venue_id)),
  [form.venue_id, venues]
 )

 const selectedSport = useMemo(
  () => sports.find((sport) => String(sport.id) === String(form.sport_id)),
  [form.sport_id, sports]
 )

 const availableSports = useMemo(() => {
  if (!selectedVenue) return sports
  return sports.filter((sport) => selectedVenue.sport_ids.includes(sport.id))
 }, [sports, selectedVenue])

 const allowedRequiredPlayers = useMemo(() => {
  const sportKey = getSportRuleKey(selectedSport?.name || '')
  return sportKey ? REQUIRED_PLAYERS_RULES[sportKey] || [] : []
 }, [selectedSport])

 const autoRequiredPlayers = useMemo(() => {
  if (!allowedRequiredPlayers.length) return null
  return allowedRequiredPlayers[form.teams_count - 2] || allowedRequiredPlayers[0]
 }, [allowedRequiredPlayers, form.teams_count])

 const hourlyOptions = useMemo(() => {
  const options = []

  slots.forEach((slot) => {
   const start = new Date(slot.start_at)
   const end = new Date(slot.end_at)
   let cursor = new Date(start)

   while (cursor.getTime() + HOUR_MS <= end.getTime()) {
    const hoursRemaining = Math.floor((end.getTime() - cursor.getTime()) / HOUR_MS)
    const nextHour = new Date(cursor.getTime() + HOUR_MS)
    options.push({
     slotId: slot.id,
     start: new Date(cursor),
     end: nextHour,
     maxDuration: Math.min(3, hoursRemaining),
     dateKey: getDateKey(cursor),
     key: `${slot.id}|${cursor.toISOString()}`,
    })
    cursor = nextHour
   }
  })

  return options.sort((a, b) => a.start - b.start)
 }, [slots])

 const slotsByDate = useMemo(() => {
  const grouped = {}
  hourlyOptions.forEach((option) => {
   if (!grouped[option.dateKey]) grouped[option.dateKey] = []
   grouped[option.dateKey].push(option)
  })
  return grouped
 }, [hourlyOptions])

 const dateOptions = useMemo(() => (
  Object.entries(slotsByDate).map(([dateKey, options]) => ({
   dateKey,
   date: options[0].start,
   count: options.length,
  }))
 ), [slotsByDate])

 useEffect(() => {
  if (!dateOptions.length) {
    setForm((prev) => (
     prev.selectedDate || prev.selectedHour
      ?
      { ...prev, selectedDate: '', selectedHour: '', duration_hours: 1 }
     : prev
    ))
   return
  }

  const selectedDateStillExists = dateOptions.some((option) => option.dateKey === form.selectedDate)
  if (!selectedDateStillExists) {
   setForm((prev) => ({ ...prev, selectedDate: dateOptions[0].dateKey, selectedHour: '', duration_hours: 1 }))
  }
 }, [dateOptions, form.selectedDate])

 const dateSlots = useMemo(() => slotsByDate[form.selectedDate] || [], [form.selectedDate, slotsByDate])

 useEffect(() => {
  if (!form.selectedHour) return
  const selectedHourStillExists = dateSlots.some((option) => option.key === form.selectedHour)
  if (!selectedHourStillExists) {
   setForm((prev) => ({ ...prev, selectedHour: '', duration_hours: 1 }))
  }
 }, [dateSlots, form.selectedHour])

 const selectedHourInfo = useMemo(() => {
  if (!form.selectedHour) return null
  return hourlyOptions.find((option) => option.key === form.selectedHour) || null
 }, [form.selectedHour, hourlyOptions])

 const maxDuration = selectedHourInfo?.maxDuration || 1

 useEffect(() => {
  if (form.duration_hours > maxDuration) {
   setForm((prev) => ({ ...prev, duration_hours: 1 }))
  }
 }, [form.duration_hours, maxDuration])

 useEffect(() => {
  if (autoRequiredPlayers === null) return
  if (Number(form.required_players) !== autoRequiredPlayers) {
   setForm((prev) => ({ ...prev, required_players: autoRequiredPlayers }))
  }
 }, [autoRequiredPlayers, form.required_players])

 const selectedEndTime = useMemo(() => {
  if (!selectedHourInfo) return null
  return new Date(selectedHourInfo.start.getTime() + form.duration_hours * HOUR_MS)
 }, [selectedHourInfo, form.duration_hours])

 const submit = async (e) => {
  e.preventDefault()
  setError('')
  setShowWalletPrompt(false)

  if (!form.sport_id) {
   setError(t('createGame.selectSportError'))
   return
  }

  if (!selectedHourInfo) {
   setError(t('createGame.selectSlot'))
   return
  }

  if (allowedRequiredPlayers.length && !allowedRequiredPlayers.includes(Number(form.required_players))) {
   setError(t('createGame.invalidRequiredPlayers', { values: allowedRequiredPlayers.join(', ') }))
   return
  }

  try {
   setSubmitting(true)
   const startAt = selectedHourInfo.start
   const endAt = new Date(startAt.getTime() + form.duration_hours * HOUR_MS)

   const event = isDemoToken(token)
    ?
     await Promise.resolve(createDemoEvent({
      sport_id: form.sport_id,
      venue_id: form.venue_id,
      slot_id: selectedHourInfo.slotId,
      start_at: startAt.toISOString(),
      end_at: endAt.toISOString(),
      required_players: Number(form.required_players),
      teams_count: Number(form.teams_count),
      duration_hours: Number(form.duration_hours),
      auto_join_creator: true,
     }))
    : await createEvent(token, {
      sport_id: form.sport_id,
      venue_id: form.venue_id,
      slot_id: selectedHourInfo.slotId,
      start_at: startAt.toISOString(),
      end_at: endAt.toISOString(),
      required_players: Number(form.required_players),
      teams_count: Number(form.teams_count),
      duration_hours: Number(form.duration_hours),
      auto_join_creator: true,
     })

   navigate(`/games/${event.id}`)
  } catch (err) {
   const detail = String(err.message || '')
   const insufficient = detail.includes('Not enough credits')
   if (insufficient) {
    setError(
     t('createGame.notEnoughCredits', {
       defaultValue: i18n.language === 'ru'
        ?
         'РќРµРґРѕСЃС‚Р°С‚РѕС‡РЅРѕ РєСЂРµРґРёС‚РѕРІ РґР»СЏ СЃРѕР·РґР°РЅРёСЏ Рё РѕРїР»Р°С‚С‹. РџРѕРїРѕР»РЅРёС‚Рµ РєРѕС€РµР»РµРє Рё РїРѕРїСЂРѕР±СѓР№С‚Рµ СЃРЅРѕРІР°.'
       : 'Not enough credits to create and pay. Top up your wallet and try again.',
     })
    )
    setShowWalletPrompt(true)
   } else {
    setError(
     detail || t('createGame.createFailed', {
      defaultValue: i18n.language === 'ru' ? 'РќРµ СѓРґР°Р»РѕСЃСЊ СЃРѕР·РґР°С‚СЊ РёРіСЂСѓ. РџРѕРїСЂРѕР±СѓР№С‚Рµ СЃРЅРѕРІР°.' : 'Failed to create game. Please try again.',
     })
    )
   }
  } finally {
   setSubmitting(false)
  }
 }

 const locale = i18n.language === 'ru' ? 'ru-RU' : 'en-US'
 const dateFormatter = useMemo(() => new Intl.DateTimeFormat(locale, {
  weekday: 'short',
  day: 'numeric',
  month: 'short',
 }), [locale])
 const longDateFormatter = useMemo(() => new Intl.DateTimeFormat(locale, {
  weekday: 'long',
  day: 'numeric',
  month: 'long',
 }), [locale])
 const timeFormatter = useMemo(() => new Intl.DateTimeFormat(locale, {
  hour: '2-digit',
  minute: '2-digit',
 }), [locale])

 const getSportIcon = () => ''

 return (
  <div className="dashboard-page">
   <div className="page-header">
    <div>
     <h1>{t('createGame.title')}</h1>
     <p className="page-subtitle">{t('createGame.subtitle')}</p>
    </div>
   </div>

   <div className="create-game-shell">
    <div className="dashboard-card glass-card create-game-form-card">
     <form className="grant-form" onSubmit={submit}>
      <div className="form-group">
       <label>{t('createGame.venue')}</label>
       <select
        value={form.venue_id}
        onChange={(e) => {
         const venueId = e.target.value
         setError('')
         setForm({
          ...INITIAL_FORM,
          venue_id: venueId,
         })
        }}
        required
       >
        <option value="">{t('createGame.selectVenue')}</option>
        {venues.map((venue) => (
         <option key={venue.id} value={venue.id}>
          {venue.name} - {venue.city} ({venue.hourly_rate}/hr)
         </option>
        ))}
       </select>
      </div>

      <div className="form-group">
       <label>{t('createGame.sport')}</label>
       <div className="create-game-chip-row">
        {availableSports.map((sport) => (
         <button
          key={sport.id}
          type="button"
          className={`sport-tab ${String(form.sport_id) === String(sport.id) ? 'active' : ''}`}
          onClick={() => {
           setError('')
           setForm((prev) => ({ ...prev, sport_id: sport.id }))
          }}
         >
          {getSportIcon(sport.name)} {getSportLabel(sport.name, t)}
         </button>
        ))}
       </div>
       {selectedVenue && availableSports.length === 0 && (
        <p className="create-game-help">{t('createGame.noSports')}</p>
       )}
      </div>

      <div className="form-group">
       <label>{t('createGame.requiredPlayers')}</label>
       {autoRequiredPlayers !== null ? (
        <>
         <div className="create-game-chip-row">
          <button type="button" className="sport-tab active">
           {autoRequiredPlayers}
          </button>
         </div>
         <p className="create-game-help">
          {t('createGame.requiredPlayersAutoHint', { teams: form.teams_count, players: autoRequiredPlayers })}
         </p>
        </>
       ) : (
        <>
        <input
         type="number"
         value={form.required_players}
         onChange={(e) => setForm((prev) => ({ ...prev, required_players: Number(e.target.value) }))}
         required
         min={2}
        />
        <p className="create-game-help">{t('createGame.requiredPlayersOpenHint')}</p>
        </>
       )}
      </div>

      <div className="form-group">
       <label>{t('createGame.teams')}</label>
       <div className="create-game-chip-row">
        {[2, 3, 4].map((teamCount) => (
         <button
          key={teamCount}
          type="button"
          className={`sport-tab ${form.teams_count === teamCount ? 'active' : ''}`}
          onClick={() => setForm((prev) => ({ ...prev, teams_count: teamCount }))}
         >
          {teamCount}
         </button>
        ))}
       </div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {showWalletPrompt && (
       <button
        type="button"
        className="btn-secondary glass-btn"
        style={{ width: '100%', marginTop: '0.5rem' }}
        onClick={() => navigate('/wallet')}
       >
        {t('wallet.title')}
       </button>
      )}
      <button
       type="submit"
       className="btn-primary glass-btn"
       style={{ width: '100%', marginTop: '0.5rem' }}
       disabled={submitting}
      >
       {submitting
         ? t('common.loading')
        : t('createGame.submitAndPay')}
      </button>
     </form>
    </div>

    <div className="dashboard-card glass-card create-game-availability-card">
     <div className="create-game-section-head">
      <div>
       <h3>{t('createGame.timeSlots')}</h3>
       <p className="create-game-help">
        {selectedVenue ? t('createGame.availabilityHint', { venue: selectedVenue.name }) : t('createGame.pickVenueToSeeAvailability')}
       </p>
      </div>
      {loadingSlots && <span className="create-game-status-pill">{t('gameDetails.loading')}</span>}
     </div>

     {!selectedVenue && (
      <div className="create-game-empty-state">
       <strong>{t('createGame.selectVenue')}</strong>
       <p>{t('createGame.pickVenueToSeeAvailability')}</p>
      </div>
     )}

     {selectedVenue && !loadingSlots && dateOptions.length === 0 && (
      <div className="create-game-empty-state">
       <strong>{t('createGame.noOpenSlots')}</strong>
       <p>{t('createGame.noOpenSlotsHint')}</p>
      </div>
     )}

     {selectedVenue && dateOptions.length > 0 && (
      <div className="create-game-availability">
       <div className="form-group">
        <label>{t('createGame.availableDates')}</label>
        <div className="create-game-date-grid">
         {dateOptions.map((option) => (
          <button
           key={option.dateKey}
           type="button"
           className={`create-game-date-card ${form.selectedDate === option.dateKey ? 'active' : ''}`}
           onClick={() => setForm((prev) => ({ ...prev, selectedDate: option.dateKey, selectedHour: '', duration_hours: 1 }))}
          >
           <span className="create-game-date-day">{dateFormatter.format(option.date)}</span>
           <span className="create-game-date-count">{t('createGame.timeCount', { count: option.count })}</span>
          </button>
         ))}
        </div>
       </div>

       <div className="form-group">
        <label>{t('createGame.availableTimes')}</label>
        <div className="create-game-time-grid">
         {dateSlots.map((option) => (
          <button
           key={option.key}
           type="button"
           className={`create-game-time-card ${form.selectedHour === option.key ? 'active' : ''}`}
           onClick={() => setForm((prev) => ({ ...prev, selectedHour: option.key, duration_hours: 1 }))}
          >
           <span className="create-game-time-main">
            {timeFormatter.format(option.start)} - {timeFormatter.format(option.end)}
           </span>
           <span className="create-game-time-meta">
            {t('createGame.upToHours', { count: option.maxDuration })}
           </span>
          </button>
         ))}
         {dateSlots.length === 0 && (
          <div className="create-game-empty-inline">{t('createGame.noTimesForDate')}</div>
         )}
        </div>
       </div>

       <div className="form-group">
        <label>{t('createGame.duration')}</label>
        <div className="create-game-chip-row">
         {Array.from({ length: maxDuration }, (_, index) => index + 1).map((hours) => (
          <button
           key={hours}
           type="button"
           className={`sport-tab ${form.duration_hours === hours ? 'active' : ''}`}
           onClick={() => setForm((prev) => ({ ...prev, duration_hours: hours }))}
          >
           {hours}{t('createGame.hoursShort')}
          </button>
         ))}
        </div>
       </div>

       <div className="create-game-summary">
        <span className="create-game-summary-label">{t('createGame.selectedSlotSummary')}</span>
        {selectedHourInfo ? (
         <div className="create-game-summary-content">
          <strong>{longDateFormatter.format(selectedHourInfo.start)}</strong>
          <span>
           {timeFormatter.format(selectedHourInfo.start)} - {selectedEndTime ? timeFormatter.format(selectedEndTime) : timeFormatter.format(selectedHourInfo.end)}
          </span>
          <span>{selectedVenue.name}</span>
         </div>
        ) : (
         <p>{t('createGame.selectSlot')}</p>
        )}
       </div>
      </div>
     )}
    </div>
   </div>
  </div>
 )
}

