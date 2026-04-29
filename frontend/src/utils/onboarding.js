const STORAGE_PREFIX = 'teamup:onboarding:'

export const ONBOARDING_QUESTIONS = [
 {
  id: 'activity_frequency',
  type: 'select',
  fallbackLabel: {
   ru: 'Как часто вы занимаетесь спортом',
   en: 'How often do you do sports',
  },
  fallbackPlaceholder: {
   ru: 'Выберите вариант',
   en: 'Select an option',
  },
  optionLabels: {
   never: { ru: 'Никогда', en: 'Never' },
   monthly_1_2: { ru: '1-2 раза в месяц', en: '1-2 times a month' },
   weekly_1_2: { ru: '1-2 раза в неделю', en: '1-2 times a week' },
   weekly_3_4: { ru: '3-4 раза в неделю', en: '3-4 times a week' },
   almost_daily: { ru: 'Почти каждый день', en: 'Almost every day' },
  },
  options: ['never', 'monthly_1_2', 'weekly_1_2', 'weekly_3_4', 'almost_daily'],
 },
 {
  id: 'sports_played',
  type: 'multiselect',
  fallbackLabel: {
   ru: 'В какие виды спорта вы играете Можно выбрать несколько',
   en: 'Which sports do you play You can choose more than one',
  },
  optionLabels: {
   football: { ru: 'Футбол', en: 'Football' },
   basketball: { ru: 'Баскетбол', en: 'Basketball' },
   volleyball: { ru: 'Волейбол', en: 'Volleyball' },
   tennis: { ru: 'Теннис', en: 'Tennis' },
   other: { ru: 'Другое', en: 'Other' },
  },
  options: ['football', 'basketball', 'volleyball', 'tennis', 'other'],
 },
 {
  id: 'skill_level',
  type: 'radio',
  fallbackLabel: {
   ru: 'Как вы оцениваете свой уровень в этих видах спорта',
   en: 'How do you rate your level in these sports',
  },
  optionLabels: {
   beginner: { ru: 'Новичок', en: 'Beginner' },
   amateur: { ru: 'Любитель', en: 'Amateur' },
   intermediate: { ru: 'Средний уровень', en: 'Intermediate' },
   advanced: { ru: 'Продвинутый', en: 'Advanced' },
  },
  options: ['beginner', 'amateur', 'intermediate', 'advanced'],
 },
 {
  id: 'team_experience',
  type: 'radio',
  fallbackLabel: {
   ru: 'Играли ли вы когда-нибудь в команде (школа, клуб, лига)',
   en: 'Have you ever played on a team (school, club, league)',
  },
  optionLabels: {
   no: { ru: 'Нет', en: 'No' },
   sometimes: { ru: 'Иногда', en: 'Sometimes' },
   regularly: { ru: 'Да, регулярно', en: 'Yes, regularly' },
  },
  options: ['no', 'sometimes', 'regularly'],
 },
 {
  id: 'endurance',
  type: 'radio',
  fallbackLabel: {
   ru: 'Как вы оцениваете свою выносливость',
   en: 'How do you rate your endurance',
  },
  optionLabels: {
   low: { ru: 'Низкая', en: 'Low' },
   medium: { ru: 'Средняя', en: 'Medium' },
   good: { ru: 'Хорошая', en: 'Good' },
   excellent: { ru: 'Отличная', en: 'Excellent' },
  },
  options: ['low', 'medium', 'good', 'excellent'],
 },
 {
  id: 'speed_reaction',
  type: 'radio',
  fallbackLabel: {
   ru: 'Как вы оцениваете свою скорость и реакцию',
   en: 'How do you rate your speed and reaction',
  },
  optionLabels: {
   low: { ru: 'Низкая', en: 'Low' },
   medium: { ru: 'Средняя', en: 'Medium' },
   good: { ru: 'Хорошая', en: 'Good' },
   excellent: { ru: 'Отличная', en: 'Excellent' },
  },
  options: ['low', 'medium', 'good', 'excellent'],
 },
 {
  id: 'competition_frequency',
  type: 'radio',
  fallbackLabel: {
   ru: 'Как часто вы участвуете в играх или турнирах',
   en: 'How often do you take part in games or tournaments',
  },
  optionLabels: {
   never: { ru: 'Никогда', en: 'Never' },
   friends_sometimes: { ru: 'Иногда с друзьями', en: 'Sometimes with friends' },
   regularly: { ru: 'Регулярно', en: 'Regularly' },
  },
  options: ['never', 'friends_sometimes', 'regularly'],
 },
 {
  id: 'notes',
  type: 'textarea',
  optional: true,
  fallbackLabel: {
   ru: 'Что вы хотите нам еще сказать',
   en: 'What else would you like to tell us',
  },
  fallbackPlaceholder: {
   ru: 'Можно коротко',
   en: 'Short note if you want',
  },
 },
]

export const ALL_ONBOARDING_QUESTIONS = [...ONBOARDING_QUESTIONS]

function getStorageKey(user) {
 const identifier = user.id || user.email
 return identifier ? `${STORAGE_PREFIX}${identifier}` : null
}

export function requiresOnboarding(user) {
 return user.role === 'player' || user.role === 'partner'
}

export function getVisibleOnboardingQuestions() {
 return [...ONBOARDING_QUESTIONS]
}

export function getOnboardingSubmission(user) {
 const key = getStorageKey(user)
 if (!key) return null

 try {
  const raw = localStorage.getItem(key)
  return raw ? JSON.parse(raw) : null
 } catch {
  return null
 }
}

export function hasCompletedOnboarding(user) {
 const submission = getOnboardingSubmission(user)
 return Boolean(user.onboarding_completed_at || submission.completedAt)
}

export function saveOnboardingSubmission(user, payload) {
 const key = getStorageKey(user)
 if (!key) return

 localStorage.setItem(
  key,
  JSON.stringify({
   answers: payload.answers || {},
   evaluation: payload.evaluation || null,
   completedAt: payload.completedAt || new Date().toISOString(),
  })
 )
}

export function getLocalizedFallback(dictionary, language) {
 if (!dictionary) return ''
 return language.startsWith('ru') ? dictionary.ru : dictionary.en
}

export function getOptionLabel(question, option, language) {
 return getLocalizedFallback(question.optionLabels?.[option], language) || option
}

export function getQuestionInitialValue(question, existingAnswers) {
 const existingValue = existingAnswers?.[question.id]
 if (question.type === 'multiselect') {
  return Array.isArray(existingValue)
   ?
    existingValue
   : typeof existingValue === 'string' && existingValue
    ?
     existingValue.split(',').filter(Boolean)
    : []
 }
 return existingValue || ''
}

export function isQuestionAnswered(question, form) {
 if (question.optional) return true
 const value = form[question.id]
 if (question.type === 'multiselect') {
  return Array.isArray(value) && value.length > 0
 }
 return Boolean(String(value || '').trim())
}

export function serializeOnboardingAnswers(questions, form) {
 return questions.reduce((acc, question) => {
  const value = form[question.id]
  acc[question.id] = question.type === 'multiselect'
   ? (Array.isArray(value) ? value.join(',') : '')
   : String(value || '').trim()
  return acc
 }, {})
}
