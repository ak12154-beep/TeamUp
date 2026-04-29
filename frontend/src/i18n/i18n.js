import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import { en } from './en';
import { ru } from './ru';

// Get saved language from localStorage or use default
const savedLanguage = localStorage.getItem('i18nextLng') || 'en';

i18n
 .use(initReactI18next)
 .init({
  resources: {
   en: { translation: en },
   ru: { translation: ru },
  },
  lng: savedLanguage,
  fallbackLng: 'en',
  interpolation: {
   escapeValue: false,
  },
 });

export default i18n;
