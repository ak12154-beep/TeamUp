import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { getSports } from '../api/sports'
import { createVenue, getVenues, updateVenue } from '../api/venues'
import '../styles/PartnerPages.css'

const initialForm = {
 name: '',
 city: '',
 address: '',
 hourly_rate: 1500,
 timezone: 'UTC',
 sport_ids: [],
}

export default function VenueManage({ token, user }) {
 const [sports, setSports] = useState([])
 const [venues, setVenues] = useState([])
 const [form, setForm] = useState(initialForm)
 const [editingId, setEditingId] = useState(null)
 const [error, setError] = useState('')
 const { t } = useTranslation()

 const ownVenues = useMemo(() => venues.filter((v) => v.partner_user_id === user.id), [venues, user.id])

 const load = async () => {
  const [sportsList, venuesList] = await Promise.all([getSports(), getVenues()])
  setSports(sportsList)
  setVenues(venuesList)
 }

 useEffect(() => {
  load().catch((e) => setError(e.message))
 }, [])

 const getSportLabel = (name) => {
  if (!name) return t('common.game')
  const normalized = name.toLowerCase()
  if (normalized.includes('football') || normalized.includes('soccer')) return t('welcome.football')
  if (normalized.includes('basketball')) return t('welcome.basketball')
  if (normalized.includes('volleyball')) return t('welcome.volleyball')
  if (normalized.includes('tennis')) return t('games.tennis')
  if (normalized.includes('padel')) return t('games.padel')
  return name
 }

 const toggleSport = (sportId) => {
  const exists = form.sport_ids.includes(sportId)
  setForm({
   ...form,
   sport_ids: exists ? form.sport_ids.filter((id) => id !== sportId) : [...form.sport_ids, sportId],
  })
 }

 const submit = async (e) => {
  e.preventDefault()
  setError('')
  try {
   const payload = { ...form, hourly_rate: Number(form.hourly_rate) }
   if (editingId) {
    await updateVenue(token, editingId, payload)
   } else {
    await createVenue(token, payload)
   }
   setForm(initialForm)
   setEditingId(null)
   await load()
  } catch (err) {
   setError(err.message)
  }
 }

 const edit = (venue) => {
  setEditingId(venue.id)
  setForm({
   name: venue.name,
   city: venue.city,
   address: venue.address,
   hourly_rate: venue.hourly_rate,
   timezone: venue.timezone,
   sport_ids: venue.sport_ids,
  })
 }

 return (
  <div className="partner-page-shell">
   <div className="partner-page-header">
    <div>
     <h1>{t('venueManage.title')}</h1>
     <p className="partner-page-subtitle">
      {editingId ? t('venueManage.cancelEdit') : t('dashboard.manageVenues')}
     </p>
    </div>
   </div>

   <section className="partner-section-card partner-form-card">
    <div className="partner-section-heading">
     <h2>{editingId ? t('venueManage.update') : t('venueManage.create')}</h2>
    </div>

    <form className="partner-form-grid" onSubmit={submit}>
     <div className="partner-form-group">
      <label>{t('venueManage.name')}</label>
      <input
       placeholder={t('venueManage.namePlaceholder')}
       value={form.name}
       onChange={(e) => setForm({ ...form, name: e.target.value })}
       required
      />
     </div>

     <div className="partner-form-group">
      <label>{t('venueManage.city')}</label>
      <input
       placeholder={t('venueManage.cityPlaceholder')}
       value={form.city}
       onChange={(e) => setForm({ ...form, city: e.target.value })}
       required
      />
     </div>

     <div className="partner-form-group partner-form-group-full">
      <label>{t('venueManage.address')}</label>
      <input
       placeholder={t('venueManage.addressPlaceholder')}
       value={form.address}
       onChange={(e) => setForm({ ...form, address: e.target.value })}
       required
      />
     </div>

     <div className="partner-form-group">
      <label>{t('venueManage.hourlyRate')}</label>
      <input
       type="number"
       placeholder={t('venueManage.ratePlaceholder')}
       value={form.hourly_rate}
       onChange={(e) => setForm({ ...form, hourly_rate: e.target.value })}
       min="1"
       required
      />
     </div>

     <div className="partner-form-group">
      <label>{t('venueManage.timezone')}</label>
      <input
       placeholder={t('venueManage.timezonePlaceholder')}
       value={form.timezone}
       onChange={(e) => setForm({ ...form, timezone: e.target.value })}
       required
      />
     </div>

     <div className="partner-form-group partner-form-group-full">
      <label>{t('venueManage.sports')}</label>
      <div className="partner-sport-pills">
       {sports.map((sport) => (
        <button
         key={sport.id}
         type="button"
         className={`partner-sport-pill ${form.sport_ids.includes(sport.id) ? 'active' : ''}`}
         onClick={() => toggleSport(sport.id)}
        >
         {getSportLabel(sport.name)}
        </button>
       ))}
      </div>
     </div>

     {error && <p className="error partner-form-group-full">{error}</p>}

     <div className="partner-form-actions partner-form-group-full">
      <button type="submit">{editingId ? t('venueManage.update') : t('venueManage.create')}</button>
      {editingId && (
       <button
        type="button"
        className="secondary"
        onClick={() => {
         setEditingId(null)
         setForm(initialForm)
        }}
       >
        {t('venueManage.cancelEdit')}
       </button>
      )}
     </div>
    </form>
   </section>

   <section className="partner-section-card">
    <div className="partner-section-heading">
     <h2>{t('venueManage.myVenues')}</h2>
     <p>{ownVenues.length}</p>
    </div>

   <div className="partner-venue-list">
    {ownVenues.map((venue) => (
     <div key={venue.id} className="partner-venue-card">
      <div className="partner-venue-card-head">
       <div>
        <h3>{venue.name}</h3>
        <p className="partner-venue-location">{venue.city}, {venue.address}</p>
       </div>
       <span className="partner-venue-rate">{venue.hourly_rate}</span>
      </div>
      <div className="partner-venue-meta">
       <span>{t('venueManage.rate')}: {venue.hourly_rate}</span>
       <span>{t('venueManage.tz')}: {venue.timezone}</span>
       <span>{t('venueManage.sports')}: {venue.sport_ids.length}</span>
      </div>
      <button className="partner-venue-edit-btn" onClick={() => edit(venue)}>
       {t('profile.editProfile')}
      </button>
     </div>
    ))}
   </div>
   </section>
  </div>
 )
}
