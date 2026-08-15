<script setup lang="ts">
/**
 * @component BaseInput
 * @description Componente de input reutilizável com suporte a labels,
 * erros de validação, ícones e toggle de visibilidade para senhas.
 */

import { computed, ref } from 'vue';

interface InputProps {
  type?: 'text' | 'email' | 'password' | 'number' | 'tel' | 'date';
  label?: string;
  placeholder?: string;
  required?: boolean;
  mask?: string;
  error?: string;
  disabled?: boolean;
  id?: string;
  /** Só para type="number". Sem `step`, o padrão do navegador é 1 e qualquer casa decimal vira valor inválido. */
  step?: string | number;
  min?: string | number;
  max?: string | number;
  /**
   * Teclado sugerido em telas de toque. Use `decimal` num campo `text` que
   * recebe número com vírgula — `type="number"` não serve para isso, porque
   * aceita só o separador decimal do locale do navegador.
   */
  inputmode?: 'text' | 'decimal' | 'numeric' | 'tel' | 'email' | 'url' | 'search';
}

const props = withDefaults(defineProps<InputProps>(), {
  type: 'text',
  required: false,
});

/**
 * `v-model.number` / `v-model.trim` só funcionam sozinhos em input NATIVO. Num
 * componente, o Vue entrega os modificadores e quem aplica é o componente — e
 * este não aplicava. Resultado: todo `v-model.number` do projeto era inerte e
 * `type="number"` devolvia string.
 *
 * Onde havia um `z.number()` na frente, isso virava perda silenciosa: a garantia
 * do item da OS saía como "90", o Zod reprovava e o `handleSubmit` do
 * vee-validate abortava sem chamar o handler e sem erro na tela — o campo
 * simplesmente voltava vazio.
 *
 * Campo vazio vira `null` (e não `''`): `''` reprova em `z.number().nullable()`
 * exatamente como a string reprovava, e o bug voltaria pela porta dos fundos.
 */
// `any` (e não `unknown`) preserva o contrato que já existia: o componente
// serve texto, número e data, e os chamadores tipam o handler como quiserem.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const [model, modelModifiers] = defineModel<any>({
  set(valor: unknown) {
    if (modelModifiers.trim && typeof valor === 'string') {
      valor = valor.trim();
    }
    if (modelModifiers.number) {
      if (valor === '' || valor === null || valor === undefined) return null;
      const numero = Number(valor);
      // Não engole o que o usuário digitou se não for número: devolver NaN
      // apagaria o campo enquanto ele ainda está escrevendo.
      return Number.isNaN(numero) ? valor : numero;
    }
    return valor;
  },
});

// `blur` não borbulha, então o listener que o Vue jogaria na div raiz nunca
// dispararia. Emitir explicitamente é o que permite normalizar um campo
// numérico só quando o usuário termina de digitar.
const emit = defineEmits<{ blur: [event: FocusEvent] }>();

const showPassword = ref(false);
const uniqueId = props.id || `input-${Math.random().toString(36).slice(2, 7)}`;

const inputType = computed(() => {
  if (props.type === 'password') {
    return showPassword.value ? 'text' : 'password';
  }
  return props.type;
});

const inputClasses = computed(() => [
  'w-full px-3 py-2 border rounded-md transition-colors duration-200 outline-none text-sm',
  'placeholder:text-gray-400 text-gray-700',
  props.error
    ? 'border-red-500 focus:border-red-500 focus:ring-1 focus:ring-red-500'
    : 'border-gray-300 focus:border-brand-primary focus:ring-1 focus:ring-brand-primary',
  props.disabled ? 'bg-gray-100 cursor-not-allowed' : 'bg-white',
  props.type === 'password' ? 'pr-10' : '',
  props.type === 'date' ? 'pr-1' : '',
  props.type === 'number' ? 'input-number-no-spinner' : ''
]);

function togglePasswordVisibility() {
  showPassword.value = !showPassword.value;
}
</script>

<template>
  <div class="w-full">
    <label
      v-if="label"
      :for="uniqueId"
      class="block select-none text-xs font-medium text-gray-700 mb-1"
    >
      {{ label }}
      <span
        v-if="required"
        class="text-red-600"
      >
         *
      </span>
    </label>

    <div class="relative">
      <input
        v-model="model"
        v-maska
        :data-maska="mask"
        :id="uniqueId"
        :type="inputType"
        :placeholder="placeholder"
        :required="required"
        :disabled="disabled"
        :inputmode="inputmode"
        :step="type === 'number' ? step : undefined"
        :min="type === 'number' ? min : undefined"
        :max="type === 'number' ? max : undefined"
        :class="inputClasses"
        @blur="emit('blur', $event)"
      />

      <button
        v-if="type === 'password'"
        type="button"
        class="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 cursor-pointer hover:text-gray-600 focus:outline-none"
        @click="togglePasswordVisibility"
        tabindex="-1"
      >
        <svg
          v-if="showPassword"
          xmlns="http://www.w3.org/2000/svg"
          class="h-4 w-4"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"
          />
        </svg>
        <svg
          v-else
          xmlns="http://www.w3.org/2000/svg"
          class="h-4 w-4"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
          />
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
          />
        </svg>
      </button>
    </div>

    <p v-if="error" class="select-none mt-0.5 text-xs text-red-500">
      {{ error }}
    </p>
  </div>
</template>
