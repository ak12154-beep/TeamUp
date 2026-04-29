import { useEffect, useState } from 'react'
import { getUserDisplayName } from '../utils/userDisplay'

export default function UserAvatar({
 user,
 src,
 name,
 email,
 alt = '',
 className = '',
 size,
 fallbackClassName = '',
 style = {},
 imgStyle = {},
}) {
 const imageSrc = src || user?.photo_url || ''
 const [failedSrc, setFailedSrc] = useState('')
 const displayName = name || getUserDisplayName(user, email || 'User')
 const fallbackLetter = displayName?.[0]?.toUpperCase() || 'U'
 const baseStyle = size
  ?
   {
    width: size,
    height: size,
   }
  : {}

 useEffect(() => {
  setFailedSrc('')
 }, [imageSrc])

 if (imageSrc && imageSrc !== failedSrc) {
  return (
   <img
    src={imageSrc}
    alt={alt}
    className={className}
    onError={() => setFailedSrc(imageSrc)}
    style={{
     ...baseStyle,
     borderRadius: '50%',
     objectFit: 'cover',
     display: 'block',
     flexShrink: 0,
     ...style,
     ...imgStyle,
    }}
   />
  )
 }

 return (
  <div
   className={[className, fallbackClassName].filter(Boolean).join(' ')}
   aria-hidden={alt === ''}
   style={{
    ...baseStyle,
    ...style,
   }}
  >
   {fallbackLetter}
  </div>
 )
}
