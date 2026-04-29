import React, { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { createSlot, deleteSlot, getVenueSlots, updateSlot } from '../api/availability'
import { getVenues } from '../api/venues'
import '../styles/VenueCalendarPage.css'

const HOURS = Array.from({ length: 12 }, (_, i) => i + 8) // 08:00 - 19:00

export default function VenueCalendar({ token, user }) {
 const [venues, setVenues] = useState([])
 const [selectedVenueId, setSelectedVenueId] = useState('')
 const [slots, setSlots] = useState([])
 const [error, setError] = useState('')
 const [modalOpen, setModalOpen] = useState(false)
 const [editingSlot, setEditingSlot] = useState(null)
 const [weekOffset, setWeekOffset] = useState(0)
 const [modalData, setModalData] = useState({
  status: 'open',
  title: '',
  startHour: 10,
  endHour: 11,
 })
 const { t, i18n } = useTranslation()

 const ownVenues = useMemo(
  () => venues.filter((v) => v.partner_user_id === user.id),
  [venues, user.id]
 )
 const selectedVenue = useMemo(
  () => venues.find((v) => v.id === selectedVenueId),
  [venues, selectedVenueId]
 )

 // Week days calculation
 const weekDays = useMemo(() => {
  const start = new Date()
  start.setDate(start.getDate() - start.getDay() + 1 + weekOffset * 7)
  start.setHours(0, 0, 0, 0)
  return Array.from({ length: 7 }, (_, i) => {
   const d = new Date(start)
   d.setDate(d.getDate() + i)
   return d
  })
 }, [weekOffset])

 const weekStart = weekDays[0]

 const loadSlots = async (venueId) => {
  if (!venueId) return
  const from = new Date(weekDays[0])
  const to = new Date(weekDays[6])
  to.setDate(to.getDate() + 1)
  const result = await getVenueSlots(venueId, from.toISOString(), to.toISOString())
  setSlots(result)
 }

 useEffect(() => {
  getVenues()
   .then((list) => {
    setVenues(list)
    const first = list.find((v) => v.partner_user_id === user.id)
    if (first) setSelectedVenueId(first.id)
   })
   .catch((e) => setError(e.message))
 }, [user.id])

 useEffect(() => {
  loadSlots(selectedVenueId).catch((e) => setError(e.message))
 }, [selectedVenueId, weekOffset])

 // Slot stats
 const stats = useMemo(() => {
  const available = slots.filter((s) => s.status === 'open').length
  const booked = slots.filter((s) => s.status === 'booked').length
  const blocked = slots.filter((s) => s.status === 'blocked').length
  return { available, booked, blocked }
 }, [slots])

 const isSameDay = (a, b) =>
  a.getFullYear() === b.getFullYear() &&
  a.getMonth() === b.getMonth() &&
  a.getDate() === b.getDate()

 const getSlotForCell = (day, hour) => {
  return slots.find((slot) => {
   const start = new Date(slot.start_at)
   return isSameDay(start, day) && start.getHours() === hour
  })
 }

 const getSlotDuration = (slot) => {
  const start = new Date(slot.start_at)
  const end = new Date(slot.end_at)
  return Math.max(1, Math.round((end - start) / (1000 * 60 * 60)))
 }

 const formatTime = (hour) => {
  if (hour === 12) return '12:00 PM'
  if (hour > 12) return `${hour - 12}:00 PM`
  return `${hour}:00 AM`
 }

 const formatDayHeader = (date) => {
  return date.toLocaleDateString(i18n.language === 'ru' ? 'ru-RU' : 'en-US', {
   weekday: 'short',
   day: 'numeric',
  })
 }

 const formatWeekHeader = () => {
  return weekStart.toLocaleDateString(i18n.language === 'ru' ? 'ru-RU' : 'en-US', {
   month: 'short',
   day: 'numeric',
   year: 'numeric',
  })
 }

 const onCellClick = (day, hour) => {
  const existing = getSlotForCell(day, hour)
  if (existing) {
   setEditingSlot(existing)
   setModalData({
    status: existing.status,
    title: existing.note || '',
    startHour: new Date(existing.start_at).getHours(),
    endHour: new Date(existing.end_at).getHours(),
    date: day,
   })
  } else {
   setEditingSlot(null)
   setModalData({
    status: 'open',
    title: '',
    startHour: hour,
    endHour: hour + 1,
    date: day,
   })
  }
  setModalOpen(true)
 }

 const onSave = async () => {
  setError('')
  try {
   const startAt = new Date(modalData.date)
   startAt.setHours(modalData.startHour, 0, 0, 0)
   const endAt = new Date(modalData.date)
   endAt.setHours(modalData.endHour, 0, 0, 0)

   const data = {
    start_at: startAt.toISOString(),
    end_at: endAt.toISOString(),
    status: modalData.status,
    note: modalData.title || null,
   }

   if (editingSlot) {
    await updateSlot(token, editingSlot.id, data)
   } else {
    await createSlot(token, selectedVenueId, data)
   }
   setModalOpen(false)
   setEditingSlot(null)
   await loadSlots(selectedVenueId)
  } catch (e) {
   setError(e.message)
  }
 }

 const onDelete = async () => {
  if (!editingSlot) return
  setError('')
  try {
   await deleteSlot(token, editingSlot.id)
   setModalOpen(false)
   setEditingSlot(null)
   await loadSlots(selectedVenueId)
  } catch (e) {
   setError(e.message)
  }
 }

 const statusColors = {
  open: { bg: '#166534', text: t('venueCal.available') },
  booked: { bg: '#1e40af', text: t('venueCal.booked') },
  blocked: { bg: '#991b1b', text: t('venueCal.blocked') },
 }

 return (
  <div className="venue-calendar-content">
   {/* Header */}
   <div className="dc-header">
    <div>
     <h1>{t('venueCal.title')}</h1>
     <p className="dc-subtitle">
     {selectedVenue ? selectedVenue.name : t('venueCal.selectVenue')} · {t('venueCal.clickHint')}
     </p>
    </div>
    <select
     className="dc-venue-select"
     value={selectedVenueId}
     onChange={(e) => setSelectedVenueId(e.target.value)}
    >
     <option value="">{t('venueCal.selectVenue')}</option>
     {ownVenues.map((venue) => (
      <option key={venue.id} value={venue.id}>
       {venue.name} ({venue.city})
      </option>
     ))}
    </select>
   </div>

   {/* Week navigation and legend */}
   <div className="dc-toolbar">
    <div className="dc-week-nav">
     <button className="dc-nav-btn" onClick={() => setWeekOffset((p) => p - 1)}>
      ←
     </button>
     <span className="dc-week-label">{formatWeekHeader()}</span>
     <button className="dc-nav-btn" onClick={() => setWeekOffset((p) => p + 1)}>
      →
     </button>
    </div>
    <div className="dc-legend">
     <span className="dc-legend-item">
      <span className="dc-legend-dot" style={{ background: '#22c55e' }}></span> {t('venueCal.available')}
     </span>
     <span className="dc-legend-item">
      <span className="dc-legend-dot" style={{ background: '#3b82f6' }}></span> {t('venueCal.booked')}
     </span>
     <span className="dc-legend-item">
      <span className="dc-legend-dot" style={{ background: '#ef4444' }}></span> {t('venueCal.blocked')}
     </span>
    </div>
    <button className="dc-add-btn" disabled={!selectedVenueId} onClick={() => onCellClick(weekDays[0], 10)}>
     {t('venueCal.addSlot')}
    </button>
   </div>

   {/* Calendar grid */}
   {selectedVenueId && (
    <div className="dc-grid-wrapper">
     <div className="dc-grid">
      {/* Header row */}
      <div className="dc-time-header"></div>
      {weekDays.map((day) => (
       <div key={day.toISOString()} className="dc-day-header">
        {formatDayHeader(day)}
       </div>
      ))}

      {/* Time rows */}
      {HOURS.map((hour) => (
       <React.Fragment key={`row-${hour}`}>
        <div className="dc-time-cell">
         {formatTime(hour)}
        </div>
        {weekDays.map((day) => {
         const slot = getSlotForCell(day, hour)
         const duration = slot ? getSlotDuration(slot) : 0
         const startTime = slot ? new Date(slot.start_at) : null
         const endTime = slot ? new Date(slot.end_at) : null

         return (
          <div
           key={`${day.toISOString()}-${hour}`}
           className="dc-cell"
           onClick={() => onCellClick(day, hour)}
          >
           {slot && (
            <div
             className="dc-slot"
             style={{
              background:
               slot.status === 'open'
                 ?
                 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)'
                : slot.status === 'booked'
                  ?
                  'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)'
                 : 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
              height: `${duration * 52 - 4}px`,
             }}
             onClick={(e) => {
              e.stopPropagation()
              onCellClick(day, hour)
             }}
            >
             <span className="dc-slot-title">
              {slot.note || statusColors[slot.status].text}
             </span>
             <span className="dc-slot-time">
              {startTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} –{' '}
              {endTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
             </span>
            </div>
           )}
          </div>
         )
        })}
       </React.Fragment>
      ))}
     </div>
    </div>
   )}

   {/* Stats cards */}
   <div className="dc-stats">
    <div className="dc-stat-card dc-stat-available">
     <div className="dc-stat-value">{stats.available}</div>
     <div className="dc-stat-label">{t('venueCal.availableSlots')}</div>
    </div>
    <div className="dc-stat-card dc-stat-booked">
     <div className="dc-stat-value">{stats.booked}</div>
     <div className="dc-stat-label">{t('venueCal.bookedSlots')}</div>
    </div>
    <div className="dc-stat-card dc-stat-blocked">
     <div className="dc-stat-value">{stats.blocked}</div>
     <div className="dc-stat-label">{t('venueCal.blockedSlots')}</div>
    </div>
   </div>

   {error && <p className="error" style={{ marginTop: '1rem' }}>{error}</p>}

   {/* Modal */}
   {modalOpen && (
    <div className="dc-modal-backdrop" onClick={() => setModalOpen(false)}>
     <div className="dc-modal" onClick={(e) => e.stopPropagation()}>
      <div className="dc-modal-header">
       <h2>{editingSlot ? t('venueCal.editSlot') : t('venueCal.createSlot')}</h2>
       <span className="dc-modal-date">
        {modalData.date.toLocaleDateString(i18n.language === 'ru' ? 'ru-RU' : 'en-US', { weekday: 'short' })}{' '}
        {formatTime(modalData.startHour)}
       </span>
      </div>

      <div className="dc-modal-body">
       {/* Status selector */}
       <label className="dc-label">{t('venueCal.status')}</label>
       <div className="dc-status-selector">
        <button
         type="button"
         className={`dc-status-btn ${modalData.status === 'open' ? 'dc-status-active' : ''}`}
         style={{ '--active-color': '#22c55e' }}
         onClick={() => setModalData((p) => ({ ...p, status: 'open' }))}
        >
         {t('venueCal.available')}
        </button>
        <button
         type="button"
         className={`dc-status-btn ${modalData.status === 'booked' ? 'dc-status-active' : ''}`}
         style={{ '--active-color': '#3b82f6' }}
         onClick={() => setModalData((p) => ({ ...p, status: 'booked' }))}
        >
         {t('venueCal.booked')}
        </button>
        <button
         type="button"
         className={`dc-status-btn ${modalData.status === 'blocked' ? 'dc-status-active' : ''}`}
         style={{ '--active-color': '#ef4444' }}
         onClick={() => setModalData((p) => ({ ...p, status: 'blocked' }))}
        >
         {t('venueCal.blocked')}
        </button>
       </div>

       {/* Date picker */}
       <label className="dc-label">{t('venueCal.date')}</label>
       <input
        type="date"
        className="dc-input"
        value={modalData.date ? `${modalData.date.getFullYear()}-${String(modalData.date.getMonth() + 1).padStart(2, '0')}-${String(modalData.date.getDate()).padStart(2, '0')}` : ''}
        onChange={(e) => {
         const [year, month, day] = e.target.value.split('-').map(Number)
         const newDate = new Date(year, month - 1, day)
         setModalData((p) => ({ ...p, date: newDate }))
        }}
       />

       {/* Time selectors */}
       <div className="dc-time-row">
        <div>
         <label className="dc-label">{t('venueCal.startTime')}</label>
         <select
          className="dc-input"
          value={modalData.startHour}
          onChange={(e) => setModalData((p) => ({ ...p, startHour: Number(e.target.value) }))}
         >
          {HOURS.map((h) => (
           <option key={h} value={h}>
            {formatTime(h)}
           </option>
          ))}
         </select>
        </div>
        <div>
         <label className="dc-label">{t('venueCal.endTime')}</label>
         <select
          className="dc-input"
          value={modalData.endHour}
          onChange={(e) => setModalData((p) => ({ ...p, endHour: Number(e.target.value) }))}
         >
          {HOURS.filter((h) => h > modalData.startHour).map((h) => (
           <option key={h} value={h}>
            {formatTime(h)}
           </option>
          ))}
          <option value={20}>8:00 PM</option>
         </select>
        </div>
       </div>

       {/* Title (for booked) */}
       {modalData.status === 'booked' && (
        <>
         <label className="dc-label">{t('venueCal.gameTitle')}</label>
         <input
          type="text"
          className="dc-input"
          placeholder={t('venueCal.gameTitlePlaceholder')}
          value={modalData.title}
          onChange={(e) => setModalData((p) => ({ ...p, title: e.target.value }))}
         />
        </>
       )}
      </div>

      <div className="dc-modal-footer">
       {editingSlot && (
        <button className="dc-delete-btn" onClick={onDelete}>
         {t('venueCal.delete')}
        </button>
       )}
       <div style={{ flex: 1 }}></div>
       <button className="dc-cancel-btn" onClick={() => setModalOpen(false)}>
        {t('venueCal.cancel')}
       </button>
       <button className="dc-save-btn" onClick={onSave}>
        {t('venueCal.save')}
       </button>
      </div>
     </div>
    </div>
   )}
  </div>
 )
}
