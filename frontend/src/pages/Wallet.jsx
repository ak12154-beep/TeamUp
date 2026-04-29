import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { adminGetUsers, adminGrantCredits } from '../api/admin'
import { getWalletMe, getWalletTransactions } from '../api/wallet'
import { getDemoWallet, isDemoToken } from '../demo/demoData'
import simbankQr from '../assets/simbank.jpeg'

export default function Wallet({ token, user, effectiveRole }) {
 const [balance, setBalance] = useState(0)
 const [transactions, setTransactions] = useState([])
 const [players, setPlayers] = useState([])
 const [grantForm, setGrantForm] = useState({ email: '', amount: 100, reason: '' })
 const [error, setError] = useState('')
 const [success, setSuccess] = useState('')
 const { t } = useTranslation()
 const whatsappHref = 'https://wa.me/996500097582?text=%D0%97%D0%B4%D1%80%D0%B0%D0%B2%D1%81%D1%82%D0%B2%D1%83%D0%B9%D1%82%D0%B5!%20%D0%9E%D1%82%D0%BF%D1%80%D0%B0%D0%B2%D0%BB%D1%8F%D1%8E%20%D1%87%D0%B5%D0%BA%20%D0%BE%D0%B1%20%D0%BE%D0%BF%D0%BB%D0%B0%D1%82%D0%B5%20%D0%B4%D0%BB%D1%8F%20%D0%BF%D0%BE%D0%BF%D0%BE%D0%BB%D0%BD%D0%B5%D0%BD%D0%B8%D1%8F%20%D0%B1%D0%B0%D0%BB%D0%B0%D0%BD%D1%81%D0%B0%20%D0%B2%20TeamUp.'
 const qrImageSrc = simbankQr
 const paymentHref = qrImageSrc
 const getTxTypeLabel = (txType) => t(`wallet.txType.${txType}`, { defaultValue: txType })

 const loadBalance = () => getWalletMe(token).then((res) => setBalance(res.balance))
 const loadTransactions = () => getWalletTransactions(token).then(setTransactions)

 useEffect(() => {
  if (isDemoToken(token)) {
   const wallet = getDemoWallet()
   setBalance(wallet.balance)
   setTransactions(wallet.transactions)
   return
  }
  loadBalance().catch((e) => setError(e.message))
  loadTransactions().catch(() => {})
  if (effectiveRole === 'admin') {
   adminGetUsers(token, 'player').then(setPlayers).catch((e) => setError(e.message))
  }
 }, [token, effectiveRole])

 const grant = async (e) => {
  e.preventDefault()
  setError('')
  try {
   await adminGrantCredits(token, {
    email: grantForm.email,
    amount: Number(grantForm.amount),
    reason: grantForm.reason || undefined,
   })
   await loadBalance()
   await loadTransactions()
   setGrantForm({ email: '', amount: 100, reason: '' })
   setSuccess(t('wallet.creditsGranted'))
  } catch (err) {
   setError(err.message)
  }
 }

 return (
  <div className="dashboard-page">
   <div className="page-header">
    <div>
     <h1>{t('wallet.title')}</h1>
     <p className="page-subtitle">{t('wallet.subtitle')}</p>
    </div>
   </div>

   {/* Balance Card */}
   <div className="dashboard-card glass-card wallet-hero wallet-hero-card" style={{ textAlign: 'center', padding: '2.5rem', marginBottom: '1.5rem' }}>
    <div className="wallet-balance">
     <span className="wallet-label">{t('wallet.currentBalance')}</span>
     <span className="wallet-amount wallet-hero-amount">{balance}</span>
     <span className="wallet-credits">{t('wallet.creditsAvailable')}</span>
    </div>
   </div>

   {/* Top up for Players */}
   {effectiveRole === 'player' && (
    <div className="dashboard-card glass-card wallet-topup-card" style={{ marginBottom: '1.5rem' }}>
     <div className="wallet-topup-header">
      <div>
       <h3>{t('wallet.topUpTitle')}</h3>
       <p className="wallet-topup-subtitle">{t('wallet.topUpSubtitle')}</p>
      </div>
      <a href={paymentHref} className="btn-primary glass-btn wallet-topup-link">
       {t('wallet.topUpPaymentLink')}
      </a>
     </div>

     <div className="wallet-topup-grid">
      <div className="wallet-qr-placeholder">
       <div className="wallet-qr-box">
        <a href={qrImageSrc} target="_blank" rel="noreferrer">
         <img
          src={qrImageSrc}
          alt="QR code for wallet top up"
          className="wallet-qr-image"
         />
        </a>
       </div>
       <p className="wallet-qr-note">{t('wallet.qrNote')}</p>
      </div>

      <div className="wallet-topup-steps">
       <div className="wallet-topup-step">
        <span className="wallet-step-index">1</span>
        <div>
         <strong>{t('wallet.stepPayTitle')}</strong>
         <p>{t('wallet.stepPayDesc')}</p>
        </div>
       </div>
       <div className="wallet-topup-step">
        <span className="wallet-step-index">2</span>
        <div>
         <strong>{t('wallet.stepReceiptTitle')}</strong>
         <p>{t('wallet.stepReceiptDesc')}</p>
        </div>
       </div>
       <div className="wallet-topup-step">
        <span className="wallet-step-index">3</span>
        <div>
         <strong>{t('wallet.stepWaitTitle')}</strong>
         <p>{t('wallet.stepWaitDesc')}</p>
        </div>
       </div>
      </div>
     </div>

     <div className="wallet-topup-actions">
      <a
       href={whatsappHref}
       target="_blank"
       rel="noreferrer"
       className="btn-primary glass-btn wallet-whatsapp-btn"
      >
       {t('wallet.sendReceiptWhatsapp')}
      </a>
      <p className="wallet-topup-footnote">{t('wallet.topUpFootnote')}</p>
     </div>
    </div>
   )}

   {error && <div className="alert alert-error">{error}</div>}
   {success && <div className="alert alert-success">{success}</div>}

   {/* Transaction History */}
   {transactions.length > 0 && (
    <div className="dashboard-card glass-card">
     <h3>{t('wallet.transactionHistory')}</h3>
     <div className="transactions-list">
      {transactions.map((tx) => (
       <div key={tx.id} className="transaction-item">
        <div className={`tx-type ${tx.tx_type}`}>
         {tx.tx_type === 'grant' && '💰'}
         {tx.tx_type === 'refund' && '↩️'}
         {tx.tx_type === 'spend' && '💸'}
         {tx.tx_type === 'credit' && '✨'}
        </div>
        <div className="tx-details">
         <div className="tx-user">{getTxTypeLabel(tx.tx_type)}</div>
         <div className="tx-time">{new Date(tx.created_at).toLocaleDateString()}</div>
        </div>
        <div className={`tx-amount ${tx.tx_type}`}>
         {tx.tx_type === 'spend' ? '-' : '+'}{tx.amount} cr
        </div>
       </div>
      ))}
     </div>
    </div>
   )}

   {/* Admin Grant Form */}
   {effectiveRole === 'admin' && (
    <div className="dashboard-card glass-card" style={{ marginTop: '1.5rem' }}>
     <h3>{t('wallet.grantAdmin')}</h3>
     <form onSubmit={grant} className="grant-form">
      <div className="form-group">
       <label>{t('wallet.player')}</label>
       <select value={grantForm.email} onChange={(e) => setGrantForm({ ...grantForm, email: e.target.value })} required>
        <option value="">{t('wallet.selectPlayer')}</option>
        {players.map((p) => (<option key={p.id} value={p.email}>{p.email}</option>))}
       </select>
      </div>
      <div className="form-group">
       <label>{t('admin.amount')}</label>
       <input type="number" value={grantForm.amount} onChange={(e) => setGrantForm({ ...grantForm, amount: Number(e.target.value) })} min={1} required />
      </div>
      <div className="form-group">
       <label>{t('wallet.reason')}</label>
       <input placeholder={t('wallet.reasonPlaceholder')} value={grantForm.reason} onChange={(e) => setGrantForm({ ...grantForm, reason: e.target.value })} />
      </div>
      <button type="submit" className="btn-primary glass-btn">💰 {t('wallet.grant')}</button>
     </form>
    </div>
   )}
  </div>
 )
}
