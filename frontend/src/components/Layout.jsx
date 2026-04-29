
import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useLocation } from 'react-router-dom';
import { getMyNotifications, markAllNotificationsRead } from '../api/users';
import { rateEvent } from '../api/events';
import logoSrc from '../assets/logo.png';
import ChatAssistant from './ChatAssistant';
import UserAvatar from './UserAvatar';
import { isDemoToken } from '../demo/demoData';
import { getUserDisplayName } from '../utils/userDisplay';

const MONTHS = {
 Jan: 0,
 Feb: 1,
 Mar: 2,
 Apr: 3,
 May: 4,
 Jun: 5,
 Jul: 6,
 Aug: 7,
 Sep: 8,
 Oct: 9,
 Nov: 10,
 Dec: 11,
}

function parseMonthDayTime(label, pattern) {
 const currentYear = new Date().getFullYear()
 if (pattern === 'event-created') {
  const match = label.match(/^([A-Z][a-z]{2}) (\d{2}), (\d{2}):(\d{2})$/)
  if (!match) return null
  const [, monthText, dayText, hoursText, minutesText] = match
  const month = MONTHS[monthText]
  if (month === undefined) return null
  return new Date(currentYear, month, Number(dayText), Number(hoursText), Number(minutesText))
 }

 const match = label.match(/^([A-Z][a-z]{2}) (\d{2}) at ? (\d{2}) : (\d{2})$/)
 if (!match) return null
 const [, monthText, dayText, hoursText, minutesText] = match
 const month = MONTHS[monthText]
 if (month === undefined) return null
 return new Date(currentYear, month, Number(dayText), Number(hoursText), Number(minutesText))
}

function formatNotification(notification, t, locale) {
 const rangeDateFormatter = new Intl.DateTimeFormat(locale, {
  weekday: 'short',
  day: 'numeric',
  month: 'short',
 })
 const rangeTimeFormatter = new Intl.DateTimeFormat(locale, {
  hour: '2-digit',
  minute: '2-digit',
 })
 const stampFormatter = new Intl.DateTimeFormat(locale, {
  day: 'numeric',
  month: 'short',
  hour: '2-digit',
  minute: '2-digit',
 })

 const createdAtLabel = stampFormatter.format(new Date(notification.created_at))

 if (notification.title === 'Game Created') {
  const match = notification.message.match(/^(.+) created (.+) at (.+) for ([A-Z][a-z]{2} \d{2}, \d{2}:\d{2}) - (\d{2}:\d{2})\. Please update your calendar and mark this time as booked\.$/)
  if (match) {
   const [, player, sport, venue, startLabel, endLabel] = match
   const start = parseMonthDayTime(startLabel, 'event-created')
   const endParts = endLabel.match(/^(\d{2}):(\d{2})$/)
   const end = start && endParts
    ? new Date(start.getFullYear(), start.getMonth(), start.getDate(), Number(endParts[1]), Number(endParts[2]))
    : null

   return {
    icon: '',
    variant: 'booking',
    title: t('notif.gameCreatedTitle'),
    body: t('notif.gameCreatedBody', { player, sport, venue }),
    meta: venue,
    timeLabel: start && end
     ? `${rangeDateFormatter.format(start)} • ${rangeTimeFormatter.format(start)} - ${rangeTimeFormatter.format(end)}`
     : `${startLabel} - ${endLabel}`,
    action: t('notif.gameCreatedAction'),
    createdAtLabel,
   }
  }
 }

 if (notification.title === 'New Booking') {
  const match = notification.message.match(/^(.+) joined (.+) at (.+) on ([A-Z][a-z]{2} \d{2} at \d{2}:\d{2})$/)
  if (match) {
   const [, player, sport, venue, whenLabel] = match
   const when = parseMonthDayTime(whenLabel, 'booking-joined')
   return {
    icon: '',
    variant: 'join',
    title: t('notif.joinedTitle'),
    body: t('notif.joinedBody', { player, sport, venue }),
    meta: venue,
    timeLabel: when ? `${rangeDateFormatter.format(when)} • ${rangeTimeFormatter.format(when)}` : whenLabel,
    action: t('notif.joinedAction'),
    createdAtLabel,
   }
  }
 }

 if (notification.title === 'Credit Request') {
  const match = notification.message.match(/^(.+) requested (\d+) credits$/)
  if (match) {
   const [, user, amount] = match
   return {
    icon: '',
    variant: 'wallet',
    title: t('notif.creditRequestTitle'),
    body: t('notif.creditRequestBody', { user, amount }),
    meta: t('notif.adminAttention'),
    timeLabel: '',
    action: t('notif.creditRequestAction'),
    createdAtLabel,
   }
  }
 }

 if (notification.notification_type === 'event_rating_request') {
  const ratingMatch = notification.message.match(/^Please rate how the game '(.+)' went from 1 to 5\.$/)
  const eventTitle = ratingMatch?.[1] || ''
  return {
   icon: '',
   variant: 'rating',
   title: t('notif.rateGameTitle'),
   body: t('notif.rateGameBody', { title: eventTitle }),
   meta: eventTitle,
   timeLabel: '',
   action: t('notif.rateGameAction'),
   createdAtLabel,
   actionPayload: notification.action_payload || [],
  }
 }

 if (notification.notification_type === 'event_refund') {
  const refundMatch = notification.message.match(
   /^We refunded (\d+) credits for '(.+)' because fewer than (\d+) players joined\.$/
  )
  const amount = refundMatch?.[1] || ''
  const eventTitle = refundMatch?.[2] || ''
  return {
   icon: '',
   variant: 'refund',
   title: t('notif.refundTitle'),
   body: t('notif.refundBody', { amount, title: eventTitle }),
   meta: eventTitle,
   timeLabel: '',
   action: t('notif.refundAction'),
   createdAtLabel,
   actionPayload: [],
  }
 }

 if (notification.notification_type === 'event_starting_soon') {
  return {
   icon: '',
   variant: 'booking',
   title: t('notif.gameSoonTitle'),
   body: notification.message,
   meta: '',
   timeLabel: '',
   action: t('notif.gameSoonAction'),
   createdAtLabel,
   actionPayload: [],
  }
 }

 return {
  icon: '',
  variant: 'default',
  title: notification.title,
  body: notification.message,
  meta: '',
  timeLabel: '',
  action: '',
  createdAtLabel,
  actionPayload: [],
 }
}

const PLAYER_NAV = [
 { path: '/dashboard', icon: '', labelKey: 'nav.home' },
 { path: '/games', icon: '', labelKey: 'nav.allGames' },
 { path: '/games/create', icon: '', labelKey: 'nav.createGame' },
 { path: '/leaderboard', icon: '', labelKey: 'nav.leaderboard' },
 { path: '/wallet', icon: '', labelKey: 'nav.wallet' },
 { path: '/profile', icon: '', labelKey: 'nav.profile' },
]

const PARTNER_NAV = [
 { path: '/dashboard', icon: '', labelKey: 'nav.dashboard' },
 { path: '/partner/analytics', icon: '', labelKey: 'nav.analytics' },
 { path: '/partner/venues', icon: '', labelKey: 'nav.myVenues' },
 { path: '/partner/calendar', icon: '', labelKey: 'nav.calendar' },
]

const ADMIN_NAV = [
 { path: '/dashboard', icon: '', labelKey: 'nav.dashboard' },
 { path: '/admin/users', icon: '', labelKey: 'nav.users' },
 { path: '/games', icon: '', labelKey: 'nav.games' },
 { path: '/admin', icon: '', labelKey: 'nav.walletControl' },
]

export default function Layout({ children, user, token, onLogout, effectiveRole }) {
 const location = useLocation();
 const [notifications, setNotifications] = useState([]);
 const [showNotifs, setShowNotifs] = useState(false);
 const [mobileNavOpen, setMobileNavOpen] = useState(false);
 const { t, i18n } = useTranslation();
 const isDemo = isDemoToken(token)

 useEffect(() => {
  if (token && !isDemo) {
   getMyNotifications(token).then(setNotifications).catch(() => {});
  }
 }, [token, location.pathname, isDemo]);

 useEffect(() => {
  setMobileNavOpen(false);
  setShowNotifs(false);
 }, [location.pathname]);

 useEffect(() => {
  document.body.classList.toggle('nav-open', mobileNavOpen);

  return () => {
   document.body.classList.remove('nav-open');
  };
 }, [mobileNavOpen]);

 useEffect(() => {
  const handleEscape = (event) => {
   if (event.key === 'Escape') {
    setMobileNavOpen(false);
    setShowNotifs(false);
   }
  };

  window.addEventListener('keydown', handleEscape);
  return () => window.removeEventListener('keydown', handleEscape);
 }, []);

 const unread = notifications.filter(n => !n.is_read).length;
 const locale = i18n.language === 'ru' ? 'ru-RU' : 'en-US'
 const formattedNotifications = useMemo(
  () => notifications.slice(0, 10).map((notification) => ({
   raw: notification,
   view: formatNotification(notification, t, locale),
  })),
  [notifications, t, locale]
 )

 const handleMarkAllRead = async () => {
  if (token) {
   await markAllNotificationsRead(token);
   setNotifications(notifications.map(n => ({ ...n, is_read: true })));
  }
 };

 const handleNotificationAction = async (notificationId, eventId, ratingValue) => {
  if (!token || !eventId || !ratingValue) return;
  try {
   await rateEvent(token, eventId, ratingValue);
   setNotifications((current) => current.map((notification) => (
    notification.id === notificationId
     ? {
       ...notification,
       is_read: true,
       action_payload: [],
       message: t('notif.rateSubmitted', { rating: ratingValue }),
      }
     : notification
   )));
  } catch {
   // keep existing notification state if submit fails
  }
 };

 const navItems = effectiveRole === 'partner'
  ? PARTNER_NAV
  : effectiveRole === 'admin'
   ? ADMIN_NAV
   : PLAYER_NAV;

 return (
  <div className="app-layout">
   <div
    className={`mobile-nav-overlay ${mobileNavOpen ? 'is-visible' : ''}`}
    onClick={() => setMobileNavOpen(false)}
    aria-hidden={!mobileNavOpen}
   />

   {/* Sidebar */}
   <aside className={`sidebar ${mobileNavOpen ? 'is-open' : ''}`}>
    <Link to="/dashboard" className="sidebar-brand">
     <img src={logoSrc} alt="TeamUp" className="sidebar-logo" />
     <span>TeamUp</span>
    </Link>

    <nav className="sidebar-nav">
     {navItems.map((item) => (
      <Link
       key={item.path}
       to={item.path}
       className={`sidebar-link ${location.pathname === item.path ? 'active' : ''}`}
      >
       <span className="sidebar-icon">{item.icon}</span>
       <span className="sidebar-label">{t(item.labelKey)}</span>
      </Link>
     ))}
    </nav>

    <div className="sidebar-footer">
     <div className="sidebar-user">
      <UserAvatar user={user} alt="" className="sidebar-avatar" />
      <div className="sidebar-user-info">
       <span className="sidebar-user-name">{getUserDisplayName(user)}</span>
       <span className="sidebar-user-role">
        {t(`role.${effectiveRole || user.role || 'player'}`)}{isDemo ? ' • Demo' : ''}
       </span>
      </div>
     </div>
     <button className="sidebar-logout" onClick={onLogout}>
      {t('nav.logout')}
     </button>
    </div>
   </aside>

   {/* Main content */}
   <main className="main-content">
    {/* Top bar */}
    <header className="top-bar">
     <div className="top-bar-left">
      <button
       type="button"
       className="mobile-menu-btn"
       onClick={() => setMobileNavOpen((current) => !current)}
       aria-label={mobileNavOpen ? 'Close navigation' : 'Open navigation'}
       aria-expanded={mobileNavOpen}
      >
       <span></span>
       <span></span>
       <span></span>
      </button>
      <Link to="/dashboard" className="top-bar-brand" aria-label="TeamUp">
       <img src={logoSrc} alt="TeamUp" className="top-bar-brand-logo" />
       <span className="top-bar-brand-text">TeamUp</span>
      </Link>
     </div>
     <div className="top-bar-right">
      <div className="top-bar-secondary">
       {!isDemo && (
        <ChatAssistant
         user={user}
         token={token}
         effectiveRole={effectiveRole}
         onToggle={(isOpen) => isOpen && setShowNotifs(false)}
        />
       )}
       {!isDemo && (
        <div className="top-bar-popover">
         <button type="button" className="notification-btn" onClick={() => setShowNotifs(!showNotifs)}>
           {unread > 0 && <span className="notif-badge">{unread}</span>}
         </button>
         {showNotifs && (
          <div className="notif-dropdown glass-card">
           <div className="notif-header">
            <div className="notif-header-main">
             <strong>{t('nav.notifications')}</strong>
             {unread > 0 && (
              <button className="notif-mark-read" onClick={handleMarkAllRead}>
               {t('nav.markAllRead')}
              </button>
             )}
            </div>
            <button
             type="button"
             className="notif-close"
             onClick={() => setShowNotifs(false)}
             aria-label={t('chat.close')}
            >
             &times;
            </button>
           </div>
           <div className="notif-list">
            {notifications.length === 0 ? (
             <div className="notif-empty">{t('nav.noNotifications')}</div>
            ) : formattedNotifications.map(({ raw, view }) => (
             <div
              key={raw.id}
              className={`notif-card notif-${view.variant} ${raw.is_read ? 'is-read' : 'is-unread'}`}
             >
              <div className="notif-card-top">
               <div className="notif-icon">{view.icon}</div>
               <div className="notif-main">
                <div className="notif-title-row">
                 <div className="notif-title">{view.title}</div>
                 <div className="notif-time-stamp">{view.createdAtLabel}</div>
                </div>
                <div className="notif-body">{view.body}</div>
               </div>
              </div>
              {view.timeLabel && <div className="notif-time-chip">{view.timeLabel}</div>}
              {view.action && <div className="notif-action">{view.action}</div>}
              {view.actionPayload.length > 0 && (
               <div className="notif-actions">
                {view.actionPayload.map((action) => (
                 <button
                  key={`${raw.id}-${action.value}`}
                  className="btn-secondary glass-btn notif-action-btn"
                  onClick={() => handleNotificationAction(raw.id, action.event_id, action.value)}
                 >
                  {action.label}
                 </button>
                ))}
               </div>
              )}
              {view.meta && <div className="notif-meta">{view.meta}</div>}
             </div>
            ))}
           </div>
          </div>
         )}
        </div>
       )}
       <Link to="/profile" className="top-bar-profile-link" aria-label={t('nav.profile')}>
        <div className="top-bar-profile-ring">
         <UserAvatar user={user} alt="" className="user-avatar-small" />
        </div>
       </Link>
      </div>
     </div>
    </header>

    {/* Page content */}
    <div className="page-content">
     {children}
    </div>
   </main>
  </div>
 );
}
