import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { login } from '../api/auth'
import logoSrc from '../assets/logo.png'
import '../styles/Auth.css'

export default function Login({ onAuth }) {
 const navigate = useNavigate()
 const [form, setForm] = useState({ email: '', password: '' })
 const [error, setError] = useState('')
 const { t } = useTranslation()

 const submit = async (e) => {
  e.preventDefault()
  setError('')
  try {
   await login(form)
   onAuth()
   navigate('/dashboard')
  } catch (err) {
   setError(err.message)
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
    <h1>{t('auth.welcomeBack')}</h1>
    <p className="auth-subtitle">{t('auth.signInSubtitle')}</p>
    <form onSubmit={submit} className="auth-form">
     <div className="auth-field">
      <label>{t('auth.email')}</label>
      <input
       type="email"
       placeholder={t('auth.emailPlaceholder')}
       value={form.email}
       onChange={(e) => setForm({ ...form, email: e.target.value })}
       required
      />
     </div>
     <div className="auth-field">
      <label>{t('auth.password')}</label>
      <input
       type="password"
       placeholder={t('auth.passwordPlaceholder')}
       value={form.password}
       onChange={(e) => setForm({ ...form, password: e.target.value })}
       required
      />
     </div>
     {error && <p className="auth-error">{error}</p>}
     <button type="submit" className="auth-submit">{t('auth.login')}</button>
    </form>
    <p className="auth-switch">
     {t('auth.noAccount')} <Link to="/register">{t('auth.createAccount')}</Link>
    </p>
   </div>
  </div>
 )
}
