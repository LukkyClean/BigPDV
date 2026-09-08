import { inject, provide, ref, type InjectionKey, type Ref } from 'vue';

type FiscalSaveFn = () => Promise<void>;

const OS_FISCAL_SAVE_KEY: InjectionKey<Ref<FiscalSaveFn | null>> = Symbol('os-fiscal-save');

/**
 * Chamado pelo OSFormModal para criar o slot de callback.
 * Retorna um ref que, quando preenchido pelo NotaFiscalSection,
 * pode ser chamado em onUpdateSuccess.
 */
export function provideOSFiscalSave() {
  const saveFn = ref<FiscalSaveFn | null>(null);
  provide(OS_FISCAL_SAVE_KEY, saveFn);
  return saveFn;
}

/**
 * Chamado pelo NotaFiscalSection para registrar sua função de save.
 */
export function registerOSFiscalSave(fn: FiscalSaveFn) {
  const saveFn = inject(OS_FISCAL_SAVE_KEY, null);
  if (saveFn) saveFn.value = fn;
}
