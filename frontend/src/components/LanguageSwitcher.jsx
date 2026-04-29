import { useTranslation } from 'react-i18next'

export default function LanguageSwitcher({ className = '', fullWidth = false }) {
 const { i18n } = useTranslation()

 const handleLanguageChange = (lng) => {
  i18n.changeLanguage(lng)
  localStorage.setItem('i18nextLng', lng)
 }

 return (
  <div className={`language-switcher ${fullWidth ? 'full-width' : ''} ${className}`.trim()}>
   <button
    type="button"
    onClick={() => handleLanguageChange('en')}
    className={`lang-btn ${i18n.language === 'en' ? 'active' : ''}`}
   >
    EN
   </button>
   <button
    type="button"
    onClick={() => handleLanguageChange('ru')}
    className={`lang-btn ${i18n.language === 'ru' ? 'active' : ''}`}
   >
    RU
   </button>
  </div>
 )
}
