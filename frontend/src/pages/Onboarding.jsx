import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { evaluateOnboarding } from '../api/ai'
import logoSrc from '../assets/logo.png'
import '../styles/Auth.css'
import {
  ALL_ONBOARDING_QUESTIONS,
  getLocalizedFallback,
  getOnboardingSubmission,
  getOptionLabel,
  getQuestionInitialValue,
  getVisibleOnboardingQuestions,
  hasCompletedOnboarding,
  isQuestionAnswered,
  requiresOnboarding,
  saveOnboardingSubmission,
  serializeOnboardingAnswers,
} from '../utils/onboarding'

function getSafeOnboardingError(language) {
 return language.startsWith('ru') ?
   'Сейчас не удалось оценить уровень. Попробуйте еще раз чуть позже.'
  : 'We could not estimate your level right now. Please try again a bit later.'
}

function buildInitialForm(user) {
 const existingAnswers = getOnboardingSubmission(user).answers || {}
 return ALL_ONBOARDING_QUESTIONS.reduce((acc, question) => {
  acc[question.id] = getQuestionInitialValue(question, existingAnswers)
  return acc
 }, {})
}

export default function Onboarding({ user, token }) {
 const navigate = useNavigate()
 const { t, i18n } = useTranslation()
 const [form, setForm] = useState(() => buildInitialForm(user))
 const [error, setError] = useState('')
 const [submitting, setSubmitting] = useState(false)
 const [result, setResult] = useState(() => getOnboardingSubmission(user).evaluation || null)

 const visibleQuestions = useMemo(() => getVisibleOnboardingQuestions(form), [form])
 const isComplete = useMemo(
  () => visibleQuestions.every((question) => isQuestionAnswered(question, form)),
  [form, visibleQuestions]
 )

 if (!user) {
  return <div className="container">{t('common.loading')}</div>
 }

 if (!requiresOnboarding(user)) {
  return <Navigate to="/dashboard" replace />
 }

 if (hasCompletedOnboarding(user)) {
  return <Navigate to="/dashboard" replace />
 }

 const tOrFallback = (key, fallback) => {
  if (!key) return getLocalizedFallback(fallback, i18n.language)
  const translated = t(key)
  return translated === key ? getLocalizedFallback(fallback, i18n.language) : translated
 }

 const update = (questionId, value) => {
  setForm((current) => ({ ...current, [questionId]: value }))
 }

 const toggleMultiValue = (questionId, option) => {
  setForm((current) => {
   const existing = Array.isArray(current[questionId]) ? current[questionId] : []
   const nextValues = existing.includes(option)
     ? existing.filter((item) => item !== option)
    : [...existing, option]
   return { ...current, [questionId]: nextValues }
  })
 }

 const submit = async (e) => {
  e.preventDefault()
  setError('')

  if (!isComplete) {
   setError(t('onboarding.validation'))
   return
  }

  setSubmitting(true)
  try {
   const answers = serializeOnboardingAnswers(visibleQuestions, form)
   const evaluation = await evaluateOnboarding(answers, i18n.language, token)
   setResult(evaluation)
  } catch {
   setError(getSafeOnboardingError(i18n.language))
  } finally {
   setSubmitting(false)
  }
 }

 const continueToDashboard = () => {
  if (!result) return
  const answers = serializeOnboardingAnswers(visibleQuestions, form)
  saveOnboardingSubmission(user, { answers, evaluation: result })
  navigate('/dashboard', { replace: true })
 }

 return (
  <div className="auth-page onboarding-page">
   <div className="auth-container onboarding-container">
    <Link to="/" className="auth-logo">
     <img src={logoSrc} alt="TeamUp" />
     <span>TeamUp</span>
    </Link>

    <div className="onboarding-badge">{t('onboarding.badge')}</div>
    <h1>{t('onboarding.title')}</h1>
    <p className="auth-subtitle">{t('onboarding.subtitle')}</p>

    <form onSubmit={submit} className="auth-form onboarding-form">
     {visibleQuestions.map((question, index) => (
      <div key={question.id} className="auth-field onboarding-field">
       <label>
        {index + 1}. {tOrFallback(question.labelKey, question.fallbackLabel)}
       </label>

       {question.type === 'select' && (
        <select
         value={form[question.id]}
         onChange={(e) => update(question.id, e.target.value)}
          required
        >
         <option value="">{tOrFallback(question.placeholderKey, question.fallbackPlaceholder)}</option>
         {question.options.map((option) => (
          <option key={option} value={option}>
           {getOptionLabel(question, option, i18n.language)}
          </option>
         ))}
        </select>
       )}

       {question.type === 'multiselect' && (
        <div className="onboarding-radio-group">
         {question.options.map((option) => {
          const selectedValues = Array.isArray(form[question.id]) ? form[question.id] : []
          const active = selectedValues.includes(option)
          return (
           <label key={option} className={`onboarding-radio ${active ? 'active' : ''}`}>
            <input
             type="checkbox"
             checked={active}
             onChange={() => toggleMultiValue(question.id, option)}
            />
            <span>{getOptionLabel(question, option, i18n.language)}</span>
           </label>
          )
         })}
        </div>
       )}

       {question.type === 'radio' && (
        <div className="onboarding-radio-group">
         {question.options.map((option) => (
          <label key={option} className={`onboarding-radio ${form[question.id] === option ? 'active' : ''}`}>
           <input
            type="radio"
            name={question.id}
            value={option}
            checked={form[question.id] === option}
            onChange={(e) => update(question.id, e.target.value)}
           />
           <span>{getOptionLabel(question, option, i18n.language)}</span>
          </label>
         ))}
        </div>
       )}

       {question.type === 'textarea' && (
        <textarea
         value={form[question.id]}
         onChange={(e) => update(question.id, e.target.value)}
         placeholder={tOrFallback(question.placeholderKey, question.fallbackPlaceholder)}
         rows={4}
         required={!question.optional}
        />
       )}
      </div>
     ))}

     {error && <p className="auth-error">{error}</p>}

     {!result && (
      <button type="submit" className="auth-submit" disabled={submitting}>
       {submitting ? (i18n.language.startsWith('ru') ? 'Считаем ваш уровень...' : 'Calculating your level...') : t('onboarding.submit')}
      </button>
     )}
    </form>

    {result && (
     <div className="dashboard-card glass-card" style={{ marginTop: '1.5rem', width: '100%' }}>
      <div className="onboarding-badge">
       {i18n.language.startsWith('ru') ? 'Рейтинг' : 'Rating'}
      </div>
      <h2 style={{ marginTop: '0.75rem' }}>{result.overall_score}/10</h2>
      <p style={{ opacity: 0.8 }}>{result.level_label}</p>
      <p style={{ opacity: 0.72 }}>
       {i18n.language.startsWith('ru') ? 'Рейтинг определён по вашим ответам и будет обновляться со временем.'
        : 'Your rating was set from your answers and may update over time.'}
      </p>
      <p style={{ lineHeight: 1.6 }}>{result.summary}</p>
      {Array.isArray(result.strengths) && result.strengths.length > 0 && (
       <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginTop: '1rem' }}>
        {result.strengths.map((item) => (
         <span key={item} className="sport-tab active">
          {item}
         </span>
        ))}
       </div>
      )}
      <button type="button" className="auth-submit" style={{ marginTop: '1rem' }} onClick={continueToDashboard}>
       {i18n.language.startsWith('ru') ? 'Продолжить в dashboard' : 'Continue to dashboard'}
      </button>
     </div>
    )}
   </div>
  </div>
 )
}


