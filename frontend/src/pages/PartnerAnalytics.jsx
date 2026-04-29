import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { adminGetPartnerStats } from '../api/admin'
import '../styles/PartnerPages.css'

function formatCredits(value) {
 return new Intl.NumberFormat().format(value || 0)
}

export default function PartnerAnalytics({ token }) {
 const [stats, setStats] = useState(null)
 const [error, setError] = useState('')
 const { t } = useTranslation()

 useEffect(() => {
  adminGetPartnerStats(token)
   .then(setStats)
   .catch((e) => setError(e.message))
 }, [token])

 const data = stats || {
  revenue_today: 0,
  revenue_week: 0,
  revenue_month: 0,
  total_revenue: 0,
  total_bookings: 0,
  upcoming_games: 0,
  venues_count: 0,
  recent_bookings: [],
 }

 return (
  <div className="partner-page-shell">
   <div className="partner-page-header">
    <div>
     <h1>{t('partnerAnalytics.title')}</h1>
     <p className="partner-page-subtitle">{t('partnerAnalytics.subtitle')}</p>
    </div>
   </div>

   <section className="partner-section-card">
    <div className="partner-section-heading">
     <h2>{t('partnerAnalytics.revenueBreakdown')}</h2>
     <p>{t('partnerAnalytics.revenueHint')}</p>
    </div>

    <div className="partner-analytics-grid">
     <div className="partner-analytics-stat">
      <span className="partner-analytics-label">{t('partnerAnalytics.today')}</span>
      <strong className="partner-analytics-value">{formatCredits(data.revenue_today)} {t('common.creditsUnit')}</strong>
     </div>
     <div className="partner-analytics-stat">
      <span className="partner-analytics-label">{t('partnerAnalytics.week')}</span>
      <strong className="partner-analytics-value">{formatCredits(data.revenue_week)} {t('common.creditsUnit')}</strong>
     </div>
     <div className="partner-analytics-stat">
      <span className="partner-analytics-label">{t('partnerAnalytics.month')}</span>
      <strong className="partner-analytics-value">{formatCredits(data.revenue_month)} {t('common.creditsUnit')}</strong>
     </div>
     <div className="partner-analytics-stat partner-analytics-stat-highlight">
      <span className="partner-analytics-label">{t('partnerAnalytics.allTime')}</span>
      <strong className="partner-analytics-value">{formatCredits(data.total_revenue)} {t('common.creditsUnit')}</strong>
     </div>
    </div>
   </section>

   <section className="partner-section-card">
    <div className="partner-section-heading">
     <h2>{t('partnerAnalytics.summary')}</h2>
     <p>{t('partnerAnalytics.summaryHint')}</p>
    </div>

    <div className="partner-analytics-summary">
     <div className="partner-analytics-summary-item">
      <span className="partner-analytics-summary-number">{data.total_bookings}</span>
      <span className="partner-analytics-summary-text">{t('dashboard.totalBookings')}</span>
     </div>
     <div className="partner-analytics-summary-item">
      <span className="partner-analytics-summary-number">{data.upcoming_games}</span>
      <span className="partner-analytics-summary-text">{t('dashboard.upcomingGamesStat')}</span>
     </div>
     <div className="partner-analytics-summary-item">
      <span className="partner-analytics-summary-number">{data.venues_count}</span>
      <span className="partner-analytics-summary-text">{t('dashboard.venues')}</span>
     </div>
    </div>
   </section>

   <section className="partner-section-card">
    <div className="partner-section-heading">
     <h2>{t('dashboard.recentBookings')}</h2>
     <p>{data.recent_bookings.length}</p>
    </div>

    <div className="partner-analytics-bookings">
     {data.recent_bookings.length === 0 ? (
      <p className="empty-text">{t('dashboard.noBookings')}</p>
     ) : (
      data.recent_bookings.slice(0, 8).map((booking) => (
       <div key={booking.event_id} className="partner-analytics-booking">
        <div>
         <div className="partner-analytics-booking-title">{booking.title || `${booking.sport_name} @ ${booking.venue_name}`}</div>
         <div className="partner-analytics-booking-meta">
          {booking.sport_name} • {booking.venue_name}
         </div>
        </div>
        <div className="partner-analytics-booking-side">
         <strong>{formatCredits(booking.revenue)} {t('common.creditsUnit')}</strong>
         <span>{booking.pricing_applied ? (t('partnerAnalytics.applied') || 'Applied') : (t('partnerAnalytics.pending') || 'Pending')}</span>
         <span>{new Date(booking.start_at).toLocaleDateString()}</span>
        </div>
       </div>
      ))
     )}
    </div>
   </section>

   {error && <p className="error">{error}</p>}
  </div>
 )
}
