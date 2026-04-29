import { http } from './http'

export function getSports() {
 return http('/sports')
}
