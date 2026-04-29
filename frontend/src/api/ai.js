import { http } from './http'

export function chatWithAssistant(messages, language, token, userRole) {
 return http('/ai/chat', {
  method: 'POST',
  body: { messages, language, user_role: userRole || undefined },
  token,
 })
}

export function evaluateOnboarding(answers, language, token) {
 return http('/ai/onboarding/evaluate', {
  method: 'POST',
  body: { answers, language },
  token,
 })
}
