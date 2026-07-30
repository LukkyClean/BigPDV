import { defineStore } from 'pinia';
import { ref } from 'vue';

const CHAVE_TEMA = 'startbig-dark-mode';
// Chave anterior ao rename do produto; lida so na migracao.
const CHAVE_TEMA_LEGADA = 'bigpdv-dark-mode';

export const useSettingsStore = defineStore('settings', () => {
  const isDarkMode = ref<boolean>(false);

  function toggleDarkMode() {
    isDarkMode.value = !isDarkMode.value;
    document.documentElement.classList.toggle('dark', isDarkMode.value);
    localStorage.setItem(CHAVE_TEMA, String(isDarkMode.value));
  }

  function init() {
    const salvo = localStorage.getItem(CHAVE_TEMA) ?? localStorage.getItem(CHAVE_TEMA_LEGADA);
    if (salvo !== null) {
      // Regrava na chave nova antes de descartar a antiga, senao a preferencia
      // se perderia no proximo carregamento.
      localStorage.setItem(CHAVE_TEMA, salvo);
      localStorage.removeItem(CHAVE_TEMA_LEGADA);
    }
    if (salvo === 'true') {
      isDarkMode.value = true;
      document.documentElement.classList.add('dark');
    }
  }

  return { isDarkMode, toggleDarkMode, init };
});
