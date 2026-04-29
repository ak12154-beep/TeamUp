import { http } from './http'

export function getWalletMe(token) {
 return http('/wallet/me', { token })
}

export function getWalletTransactions(token) {
 return http('/wallet/transactions', { token })
}
