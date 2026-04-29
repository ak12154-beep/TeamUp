import basketballCover from '../assets/game-covers/basket1.JPG'
import footballCover from '../assets/game-covers/football.JPG'
import volleyballCover from '../assets/game-covers/volleyball.JPG'

const SPORT_IMAGES = {
 football: footballCover,
 basketball: basketballCover,
 volleyball: volleyballCover,
 default: footballCover,
}

export const DEFAULT_SPORT_IMAGE = SPORT_IMAGES.default

export function getSportImage(name) {
 if (!name) return SPORT_IMAGES.default

 const normalized = name.toLowerCase()

 if (
  normalized.includes('football') ||
  normalized.includes('soccer') ||
  normalized.includes('футбол')
 ) {
  return SPORT_IMAGES.football
 }

 if (normalized.includes('basketball') || normalized.includes('баскетбол')) {
  return SPORT_IMAGES.basketball
 }

 if (normalized.includes('volleyball') || normalized.includes('волейбол')) {
  return SPORT_IMAGES.volleyball
 }

 return SPORT_IMAGES.default
}
