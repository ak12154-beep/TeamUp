export function getUserDisplayName(user, fallback = 'User') {
 const firstName = String(user.first_name || '').trim()
 const lastName = String(user.last_name || '').trim()
 const nickname = String(user.nickname || '').trim()
 const email = String(user.email || user.user_email || '').trim()
 const fullName = [firstName, lastName].filter(Boolean).join(' ').trim()
 const emailLocalPart = email.includes('@') ? email.split('@')[0] : email

 if (fullName) return fullName
 if (nickname) return nickname
 if (firstName) return firstName
 if (lastName) return lastName
 if (emailLocalPart) return emailLocalPart

 return fallback
}

export function getParticipantDisplayName(participant, fallback = 'Player') {
 const firstName = String(participant.first_name || '').trim()
 const lastName = String(participant.last_name || '').trim()
 const nickname = String(participant.nickname || '').trim()
 const email = String(participant.user_email || participant.email || '').trim()
 const fullName = [firstName, lastName].filter(Boolean).join(' ').trim()
 const emailLocalPart = email.includes('@') ? email.split('@')[0] : email

 if (fullName) return fullName
 if (nickname) return nickname
 if (firstName) return firstName
 if (lastName) return lastName
 if (emailLocalPart) return emailLocalPart

 return fallback
}
