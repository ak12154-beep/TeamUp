import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { register, sendVerificationCode } from '../api/auth'
import logoSrc from '../assets/logo.png'
import '../styles/Auth.css'

const VERIFICATION_CODE_COOLDOWN_MS = 60_000

function getRetryAfterSeconds(error) {
 if (Number.isFinite(error.retryAfter) && error.retryAfter > 0) {
  return error.retryAfter
 }

 const match = error.message.match(/(\d+)s/)
 if (!match) {
  return 0
 }

 return Number.parseInt(match[1], 10) || 0
}

export default function Register({ onAuth }) {
 const navigate = useNavigate()
 const [form, setForm] = useState({
  first_name: '',
  last_name: '',
  birth_date: '',
  email: '',
  verification_code: '',
  password: '',
 })
 const [error, setError] = useState('')
 const [info, setInfo] = useState('')
 const [sendingCode, setSendingCode] = useState(false)
 const [submitting, setSubmitting] = useState(false)
 const [cooldownUntil, setCooldownUntil] = useState(0)
 const [cooldownLeft, setCooldownLeft] = useState(0)
 const [codeSent, setCodeSent] = useState(false)
 const [acceptedLegal, setAcceptedLegal] = useState(false)
 const { t } = useTranslation()

 useEffect(() => {
  if (!cooldownUntil) {
   setCooldownLeft(0)
   return
  }

  const syncCooldown = () => {
   const nextLeft = Math.max(0, Math.ceil((cooldownUntil - Date.now()) / 1000))
   setCooldownLeft(nextLeft)
   if (nextLeft === 0) {
    setCooldownUntil(0)
   }
  }

  syncCooldown()
  const timer = setInterval(syncCooldown, 1000)
  return () => clearInterval(timer)
 }, [cooldownUntil])

 const update = (key, value) => {
  setForm((f) => ({ ...f, [key]: value }))
  if (key === 'email') {
   setCodeSent(false)
  }
 }

 const requestCode = async () => {
  setError('')
  setInfo('')
  if (!form.email.trim()) {
   setError(t('auth.enterEmailFirst'))
   return
  }

  setSendingCode(true)
  try {
   const res = await sendVerificationCode({ email: form.email })
   setInfo(res.detail || t('auth.codeSent'))
   setCooldownUntil(Date.now() + VERIFICATION_CODE_COOLDOWN_MS)
   setCodeSent(true)
  } catch (err) {
   const retryAfterSeconds = getRetryAfterSeconds(err)
   if (retryAfterSeconds > 0) {
    setCooldownUntil(Date.now() + retryAfterSeconds * 1000)
   }
   setError(err.message)
  } finally {
   setSendingCode(false)
  }
 }

 const submit = async (e) => {
  e.preventDefault()
  setError('')
  setInfo('')
  if (!acceptedLegal) {
   setError(t('auth.acceptTermsError'))
   return
  }
  setSubmitting(true)
  try {
   await register(form)
   onAuth()
   navigate('/dashboard')
  } catch (err) {
   setError(err.message)
  } finally {
   setSubmitting(false)
  }
 }

 return (
  <div className="auth-page">
   <div className="auth-container">
    <Link to="/" className="auth-back-link">← {t('auth.backToWelcome')}</Link>
    <Link to="/" className="auth-logo">
     <img src={logoSrc} alt="TeamUp" />
     <span>TeamUp</span>
    </Link>
    <h1>{t('auth.createAccount')}</h1>
    <p className="auth-subtitle">{t('auth.registerSubtitle')}</p>

    <form onSubmit={submit} className="auth-form">
     <div className="auth-name-grid">
      <div className="auth-field">
       <label>{t('auth.firstName')}</label>
       <input
        type="text"
        placeholder={t('auth.firstNamePlaceholder')}
        value={form.first_name}
        onChange={(e) => update('first_name', e.target.value)}
        required
       />
      </div>
      <div className="auth-field">
       <label>{t('auth.lastName')}</label>
       <input
        type="text"
        placeholder={t('auth.lastNamePlaceholder')}
        value={form.last_name}
        onChange={(e) => update('last_name', e.target.value)}
        required
       />
      </div>
     </div>

     <div className="auth-field">
      <label>{t('auth.birthDate')}</label>
      <input
       type="date"
       value={form.birth_date}
       onChange={(e) => update('birth_date', e.target.value)}
       required
      />
     </div>

     <div className="auth-field">
      <label>{t('auth.email')}</label>
      <div className="auth-inline-row">
       <input
        type="email"
        placeholder={t('auth.emailPlaceholder')}
        value={form.email}
        onChange={(e) => update('email', e.target.value)}
        required
       />
       <button
        type="button"
        className="auth-send-code"
        onClick={requestCode}
        disabled={sendingCode || cooldownLeft > 0}
       >
        {sendingCode ? t('auth.sending') : cooldownLeft > 0 ? `${t('auth.retryIn')} ${cooldownLeft}s` : t('auth.sendCode')}
       </button>
      </div>
      {codeSent && <small className="auth-hint">{t('auth.codeSentHint')}</small>}
     </div>

     <div className="auth-field">
      <label>{t('auth.verificationCode')}</label>
      <input
       type="text"
       placeholder={t('auth.codePlaceholder')}
       value={form.verification_code}
       onChange={(e) => update('verification_code', e.target.value)}
       required
      />
     </div>

     <div className="auth-field">
      <label>{t('auth.password')}</label>
      <input
       type="password"
       placeholder={t('auth.passwordCreatePlaceholder')}
       value={form.password}
       onChange={(e) => update('password', e.target.value)}
       required
       minLength={8}
      />
     </div>

     <div className="auth-consent">
      <label className="auth-consent-label">
       <input
        type="checkbox"
        checked={acceptedLegal}
        onChange={(e) => {
         setAcceptedLegal(e.target.checked)
         if (e.target.checked) {
          setError('')
         }
        }}
       />
       <span>
        {t('auth.acceptTermsPrefix')}{' '}
        <Link to="/legal/terms" className="auth-consent-link">{t('auth.userAgreement')}</Link>{' '}
        {t('auth.acceptTermsMiddle')}{' '}
        <Link to="/legal/privacy" className="auth-consent-link">{t('auth.privacyPolicy')}</Link>
       </span>
      </label>
     </div>

     {info && <p className="auth-info">{info}</p>}
     {error && <p className="auth-error">{error}</p>}

     <button type="submit" className="auth-submit" disabled={submitting || !acceptedLegal}>
      {submitting ? t('auth.registering') : t('auth.register')}
     </button>
    </form>

    <p className="auth-switch">
     {t('auth.haveAccount')} <Link to="/login">{t('auth.login')}</Link>
    </p>
   </div>
  </div>
 )
}
