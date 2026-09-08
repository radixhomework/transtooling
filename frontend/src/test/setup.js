import { vi } from "vitest";

// Unit tests never need real translations: return the key itself. The `t`
// function identity is stable across renders so that hooks depending on it
// do not re-run their effects endlessly.
const translate = (key, params) => (params ? `${key}:${JSON.stringify(params)}` : key);
const i18n = { language: "en" };

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: translate, i18n }),
}));
