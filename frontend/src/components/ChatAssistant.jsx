import { useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { chatWithAssistant } from '../api/ai'
import { getMyStats } from '../api/users'
import UserAvatar from './UserAvatar'

const BOT_ID = 'bot'
const USER_ID = 'user'
const MAX_HISTORY_MESSAGES = 6
const LEVEL_CHECK_ID = 'level-check'
const AI_ASSISTANT_AVATAR = '/ai-assistant.png'

function normalizeRole(role) {
 const value = String(role || '').toLowerCase()
 if (value === 'partner' || value === 'admin') return value
 return 'player'
}

function createMessage(sender, text, extra = {}) {
 return {
  id: `${sender}-${Date.now()}-${Math.random().toString(16).slice(2)}`,
  sender,
  text,
  ...extra,
 }
}

function toApiMessages(messages) {
 return messages
  .filter((message) => message.sender === USER_ID || message.sender === BOT_ID)
  .slice(-MAX_HISTORY_MESSAGES)
  .map((message) => ({
   role: message.sender === USER_ID ? 'user' : 'assistant',
   text: message.text,
  }))
}

function getSafeAssistantError(language) {
 const isRu = language.startsWith('ru')
 return isRu
  ? 'Сейчас ассистент временно недоступен. Попробуйте еще раз чуть позже.'
  : 'The assistant is temporarily unavailable right now. Please try again a bit later.'
}

function sanitizeAssistantText(text, language) {
 const value = String(text || '').trim()
 if (!value) return getSafeAssistantError(language)

 const lower = value.toLowerCase()
 const blockedPhrases = [
  'request failed',
  'openai_api_key',
  'traceback',
  'service unavailable',
  'internal server error',
  'failed with status',
 ]

 if (blockedPhrases.some((phrase) => lower.includes(phrase))) {
  return getSafeAssistantError(language)
 }

 return value
}

function getAssistantSubtitle(language, role) {
 const isRu = language.startsWith('ru')
 if (role === 'player') {
  return isRu ? 'Помощь по играм, площадкам и уровню игрока' : 'Help with games, venues, and player level'
 }
 if (role === 'partner') {
  return isRu ? 'Помощь по площадкам, календарю и аналитике партнера' : 'Help with partner venues, calendar, and analytics'
 }
 return isRu ? 'Помощь по TeamUp и админ-функциям' : 'Help with TeamUp and admin tasks'
}

function getAssistantGreeting(language, role) {
 const isRu = language.startsWith('ru')
  if (role === 'player') {
   return isRu
    ? 'Привет! Я AI-помощник TeamUp. Могу помочь с играми, площадками и показать ваш актуальный рейтинг.'
    : 'Hi! I am TeamUp AI assistant. I can help with games, venues, and show your current rating.'
  }
  if (role === 'partner') {
   return isRu
    ? 'Привет! Я AI-помощник TeamUp. Могу помочь обладателю поля с площадками, календарем  и аналитикой.'
    : 'Hi! I am TeamUp AI assistant. I can help partner accounts with venues, calendar, and analytics.'
  }
  return isRu
  ? 'Привет! Я AI-помощник TeamUp. Могу подсказать по админ-разделам и общим функциям платформы.'
  : 'Hi! I am TeamUp AI assistant. I can help with admin sections and general TeamUp features.'
}

function getQuickReplies(t, language, role) {
 const isRu = language.startsWith('ru')
 if (role === 'player') {
  return [
   { id: 'today-games', label: t('chat.quickReplyTodayGames') },
   { id: LEVEL_CHECK_ID, label: isRu ? 'Проверить мой уровень' : 'Check my level' },
   { id: 'about', label: t('chat.quickReplyAbout') },
  ]
 }

 if (role === 'partner') {
  return [
   { id: 'partner-venues', label: isRu ? 'Как управлять площадками' : 'Manage venues' },
   { id: 'partner-calendar', label: isRu ? 'Как открыть слоты в календаре' : 'Open calendar slots' },
   { id: 'partner-analytics', label: isRu ? 'Где смотреть аналитику' : 'View analytics' },
  ]
 }

 return [
  { id: 'about', label: t('chat.quickReplyAbout') },
 ]
}

export default function ChatAssistant({ className = '', onToggle, user, token, effectiveRole }) {
 const { t, i18n } = useTranslation()
 const [isOpen, setIsOpen] = useState(false)
 const [messages, setMessages] = useState([])
 const [inputValue, setInputValue] = useState('')
 const [isLoading, setIsLoading] = useState(false)
 const [showQuickReplies, setShowQuickReplies] = useState(true)
 const containerRef = useRef(null)
 const messagesRef = useRef(null)
 const assistantRole = normalizeRole(effectiveRole || user?.role)
 const quickReplies = useMemo(() => getQuickReplies(t, i18n.language, assistantRole), [t, i18n.language, assistantRole])

 useEffect(() => {
  if (!isOpen || messages.length > 0) return
  setMessages([createMessage(BOT_ID, getAssistantGreeting(i18n.language, assistantRole))])
 }, [assistantRole, i18n.language, isOpen, messages.length])

 useEffect(() => {
  if (!messagesRef.current) return
  messagesRef.current.scrollTop = messagesRef.current.scrollHeight
 }, [messages, isLoading])

 useEffect(() => {
  if (!isOpen) return undefined

  const handleClickOutside = (event) => {
   if (containerRef.current && !containerRef.current.contains(event.target)) {
    setIsOpen(false)
    onToggle?.(false)
   }
  }

  const handleEscape = (event) => {
   if (event.key === 'Escape') {
    setIsOpen(false)
    onToggle?.(false)
   }
  }

  document.addEventListener('mousedown', handleClickOutside)
  document.addEventListener('keydown', handleEscape)

  return () => {
   document.removeEventListener('mousedown', handleClickOutside)
   document.removeEventListener('keydown', handleEscape)
  }
 }, [isOpen, onToggle])

 const handleGenericSend = async (text) => {
  const userMessage = createMessage(USER_ID, text)
  const nextMessages = [...messages, userMessage]
  setMessages(nextMessages)
  setInputValue('')
  setIsLoading(true)

  try {
   const result = await chatWithAssistant(toApiMessages(nextMessages), i18n.language, token, assistantRole)
   setMessages((current) => [
    ...current,
    createMessage(BOT_ID, sanitizeAssistantText(result.text, i18n.language), {
     references: Array.isArray(result.references) ? result.references : [],
    }),
   ])
  } catch {
   setMessages((current) => [
    ...current,
    createMessage(BOT_ID, getSafeAssistantError(i18n.language)),
   ])
  } finally {
   setIsLoading(false)
  }
 }

 const handleLevelCheck = async () => {
  if (assistantRole !== 'player' || isLoading) return
  setShowQuickReplies(false)
  setIsLoading(true)
  try {
   const stats = await getMyStats(token)
   const rating = Number(stats.player_rating || 0).toFixed(1)
   const text = i18n.language.startsWith('ru') ? `Ваш рейтинг: ${rating}` : `Your rating: ${rating}`
   setMessages((current) => [...current, createMessage(BOT_ID, text)])
  } catch {
   setMessages((current) => [...current, createMessage(BOT_ID, getSafeAssistantError(i18n.language))])
  } finally {
   setIsLoading(false)
  }
 }

 const handleSendMessage = async (rawText) => {
  const text = rawText.trim()
  if (!text || isLoading) return
  setShowQuickReplies(false)
  await handleGenericSend(text)
 }

 const handleQuickReply = async (reply) => {
  if (reply.id === LEVEL_CHECK_ID) {
   await handleLevelCheck()
   return
  }

  if (reply.id === 'partner-venues') {
   setShowQuickReplies(false)
   await handleSendMessage(i18n.language.startsWith('ru') ? 'Как управлять площадками партнера' : 'How do I manage partner venues')
   return
  }

  if (reply.id === 'partner-calendar') {
   setShowQuickReplies(false)
   await handleSendMessage(i18n.language.startsWith('ru') ? 'Как открыть слоты в календаре партнера' : 'How do I open slots in partner calendar')
   return
  }

  if (reply.id === 'partner-analytics') {
   setShowQuickReplies(false)
   await handleSendMessage(i18n.language.startsWith('ru') ? 'Где смотреть аналитику партнера' : 'Where can I view partner analytics')
   return
  }

  setShowQuickReplies(false)
  await handleSendMessage(reply.label)
 }

 const handleSubmit = async (event) => {
  event.preventDefault()
  await handleSendMessage(inputValue)
 }

 const toggleChat = () => {
  setIsOpen((current) => {
   const next = !current
   onToggle?.(next)
   return next
  })
 }

 return (
  <div className={`chat-assistant ${className}`.trim()} ref={containerRef}>
   <button
    type="button"
    className={`chat-trigger ${isOpen ? 'active' : ''}`}
    onClick={toggleChat}
    aria-expanded={isOpen}
    aria-controls="ai-assistant-panel"
    aria-label={t('chat.openAssistant')}
   >
    <span aria-hidden="true">AI</span>
   </button>

   {isOpen && (
    <div className="chat-popover glass-card" id="ai-assistant-panel">
     <div className="chat-header">
      <div>
       <strong>{t('chat.title')}</strong>
       <p>{getAssistantSubtitle(i18n.language, assistantRole)}</p>
      </div>
      <button
       type="button"
       className="chat-close"
       onClick={() => {
        setIsOpen(false)
        onToggle?.(false)
       }}
       aria-label={t('chat.close')}
      >
       &times;
      </button>
     </div>

     <div className="chat-messages" ref={messagesRef}>
      {messages.map((message) => (
       <div
        key={message.id}
        className={`chat-bubble-row ${message.sender === USER_ID ? 'is-user' : 'is-bot'}`}
       >
        {message.sender === BOT_ID && (
         <UserAvatar
          src={AI_ASSISTANT_AVATAR}
          name="AI Assistant"
          alt=""
          className="chat-avatar ai"
          fallbackClassName="chat-avatar-ai-fallback"
         />
        )}
        <div className={`chat-bubble ${message.sender === USER_ID ? 'user' : 'bot'}`}>
         <div>{message.text}</div>

         {Array.isArray(message.references) && message.references.length > 0 && (
          <div className="chat-reference-list">
           {message.references.map((reference) => (
            <a
             key={`${message.id}-${reference.title}-${reference.subtitle || ''}`}
             className="chat-reference-link"
             href={reference.url || '#'}
             target={reference.url ? '_blank' : undefined}
             rel={reference.url ? 'noreferrer' : undefined}
             onClick={(event) => {
              if (!reference.url) event.preventDefault()
             }}
            >
             <strong>{reference.title}</strong>
             {reference.subtitle && <span>{reference.subtitle}</span>}
            </a>
           ))}
          </div>
         )}
        </div>
        {message.sender === USER_ID && (
         <UserAvatar user={user} alt="" className="chat-avatar user-avatar-small" />
        )}
       </div>
      ))}

      {showQuickReplies && messages.length > 0 && (
       <div className="chat-quick-replies">
        {quickReplies.map((reply) => (
         <button
          key={reply.id}
          type="button"
          className="chat-quick-reply"
          onClick={() => handleQuickReply(reply)}
         >
          {reply.label}
         </button>
        ))}
       </div>
      )}

      {isLoading && (
       <div className="chat-bubble-row is-bot">
        <div className="chat-bubble bot chat-typing">
         <span />
         <span />
         <span />
        </div>
       </div>
      )}
     </div>

     <form className="chat-input-row" onSubmit={handleSubmit}>
      <input
       type="text"
       value={inputValue}
       onChange={(event) => setInputValue(event.target.value)}
       placeholder={t('chat.inputPlaceholder')}
       className="chat-input"
      />
      <button type="submit" className="chat-send" disabled={isLoading || !inputValue.trim()}>
       {t('chat.send')}
      </button>
     </form>
    </div>
   )}
  </div>
 )
}
