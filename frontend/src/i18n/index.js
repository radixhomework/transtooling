import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import fr from "./locales/fr.json";
import en from "./locales/en.json";

const STORE_KEY = "language";

// Explicit user choice first; English is the default language.
const stored = localStorage.getItem(STORE_KEY);
const initial = stored || "en";

i18n.use(initReactI18next).init({
  resources: {
    fr: { translation: fr },
    en: { translation: en },
  },
  lng: initial,
  fallbackLng: "en",
  interpolation: { escapeValue: false },
});

export function setLanguage(lang) {
  localStorage.setItem(STORE_KEY, lang);
  i18n.changeLanguage(lang);
}

export default i18n;
