import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { getLeaderboard } from '../api/users'
import UserAvatar from '../components/UserAvatar'
import { getDemoLeaderboard, isDemoToken } from '../demo/demoData'
import { getUserDisplayName } from '../utils/userDisplay'

export default function Leaderboard({ token }) {
 const [players, setPlayers] = useState([])
 const [loading, setLoading] = useState(true)
 const [visibleCount, setVisibleCount] = useState(10)
 const { t } = useTranslation()

 useEffect(() => {
  if (isDemoToken(token)) {
   setPlayers(getDemoLeaderboard())
   setLoading(false)
   return
  }
  getLeaderboard(token)
   .then(setPlayers)
   .catch(() => {})
   .finally(() => setLoading(false))
 }, [token])

 const getMedal = (i) => {
  if (i === 0) return '🥇'
  if (i === 1) return '🥈'
  if (i === 2) return '🥉'
  return `#${i + 1}`
 }

 const formatRating = (value) => {
  if (value === null || value === undefined) return '-'
  return Number(value).toFixed(1)
 }

 const getDisplayName = (player) => getUserDisplayName(player, '')
 const visiblePlayers = players.slice(0, visibleCount)
 const hasMorePlayers = visibleCount < players.length
 const podiumOrder = [1, 0, 2]
 const mobileListPlayers = visiblePlayers.slice(3)
 const getPodiumTone = (rank) => {
  if (rank === 1) return 'gold'
  if (rank === 2) return 'silver'
  return 'bronze'
 }

 return (
  <div className="dashboard-page leaderboard-page">
   <div className="page-header">
    <div className="page-header-copy">
     <h1>{t('leaderboard.title')}</h1>
     <p className="page-subtitle">{t('leaderboard.subtitle')}</p>
    </div>
   </div>

   {loading ? (
    <div style={{ textAlign: 'center', padding: '3rem', opacity: 0.6 }}>{t('leaderboard.loading')}</div>
   ) : players.length === 0 ? (
    <div className="empty-state glass-card">
     <div className="empty-state-icon">🏆</div>
     <h3>{t('leaderboard.noPlayers')}</h3>
     <p>{t('leaderboard.joinHint')}</p>
    </div>
   ) : (
    <>
     {/* Top 3 podium */}
     <section className="leaderboard-hero glass-card">
      <div className="leaderboard-hero-copy">
       <span className="leaderboard-hero-eyebrow">{t('leaderboard.title')}</span>
       <h2 className="leaderboard-hero-title">{t('leaderboard.subtitle')}</h2>
      </div>
      <div className="leaderboard-podium">
       {podiumOrder.map((idx) => {
        const player = players[idx]
        if (!player) return null
        const rank = idx + 1
        return (
         <div
          key={player.id}
          className={`glass-card leaderboard-podium-card rank-${rank} tone-${getPodiumTone(rank)}`}
         >
          <div className="leaderboard-podium-rank-chip">{getMedal(idx)}</div>
          <div className="leaderboard-podium-avatar-wrap">
           <div className={`leaderboard-podium-avatar-ring ring-${getPodiumTone(rank)}`}>
            <UserAvatar
             src={player.photo_url}
             name={getDisplayName(player)}
             alt={getDisplayName(player)}
             className="user-avatar-small leaderboard-podium-avatar"
             size={rank === 1 ? 72 : 58}
            />
           </div>
          </div>
          <div className="leaderboard-podium-body">
           <div className="leaderboard-podium-name">
            {getDisplayName(player)}
           </div>
           <div className="leaderboard-podium-rating-block">
            <span className="leaderboard-podium-rating">
             {formatRating(player.player_rating)}
            </span>
            <span className="leaderboard-podium-rating-label">{t('dashboard.rating')}</span>
           </div>
           <div className="leaderboard-podium-games">
            <span className="leaderboard-games-icon" aria-hidden="true">🎮</span>
            <span>{player.games_played} {t('leaderboard.games')}</span>
           </div>
          </div>
         </div>
        )
       })}
      </div>
     </section>

     {/* Full leaderboard table */}
     <div className="dashboard-card glass-card leaderboard-table-card">
      <div className="leaderboard-mobile-list">
       {mobileListPlayers.map((p, i) => {
        const rank = i + 4
        return (
         <div key={`mobile-${p.id}`} className="glass-card leaderboard-mobile-item">
          <div className="leaderboard-mobile-rank">#{rank}</div>
          <div className="leaderboard-mobile-player">
           <UserAvatar
            src={p.photo_url}
            name={getDisplayName(p)}
            alt={getDisplayName(p)}
            className="user-avatar-small"
            size={36}
           />
           <div className="leaderboard-mobile-player-copy">
            <div className="leaderboard-table-name">{getDisplayName(p)}</div>
            <div className="leaderboard-mobile-meta">
             <span className="leaderboard-mobile-rating"><strong>{formatRating(p.player_rating)}</strong></span>
             <span className="leaderboard-mobile-games"><span aria-hidden="true">🎮</span> <strong>{p.games_played}</strong> {t('leaderboard.games')}</span>
            </div>
           </div>
          </div>
         </div>
        )
       })}
      </div>
      <div className="admin-table leaderboard-desktop-table">
       <table className="leaderboard-table">
       <thead>
        <tr>
         <th>{t('leaderboard.rank')}</th>
         <th>{t('leaderboard.player')}</th>
         <th>{t('dashboard.rating')}</th>
         <th>{t('leaderboard.gamesPlayed')}</th>
        </tr>
       </thead>
       <tbody>
        {visiblePlayers.map((p, i) => (
         <tr key={p.id} style={i < 3 ? { background: 'rgba(250,194,22,0.05)' } : {}}>
          <td style={{ fontWeight: 700, fontSize: '1.1rem' }}>{getMedal(i)}</td>
          <td>
           <div className="leaderboard-table-player">
            <UserAvatar
             src={p.photo_url}
             name={getDisplayName(p)}
             alt={getDisplayName(p)}
             className="user-avatar-small"
             size={32}
             style={{
              border: i < 3 ? '1px solid var(--gold)' : '1px solid rgba(255,255,255,0.12)',
             }}
            />
            <div className="leaderboard-table-player-text">
             <div className="leaderboard-table-name">{getDisplayName(p)}</div>
            </div>
           </div>
          </td>
          <td>
           <span className="gold" style={{ fontWeight: 700 }}>{formatRating(p.player_rating)}</span>
          </td>
          <td>
           <span className="gold" style={{ fontWeight: 700 }}>{p.games_played}</span>
          </td>
         </tr>
        ))}
       </tbody>
       </table>
      </div>
      {hasMorePlayers ? (
       <div className="leaderboard-more">
        <button
         type="button"
         className="btn-secondary glass-btn leaderboard-more-btn"
         onClick={() => setVisibleCount((current) => current + 10)}
        >
         {t('leaderboard.showMore')}
        </button>
       </div>
      ) : null}
     </div>
    </>
   )}
  </div>
 )
}
