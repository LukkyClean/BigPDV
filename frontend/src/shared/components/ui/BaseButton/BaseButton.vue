<script setup lang="ts">
import { computed } from 'vue';

interface ButtonProps {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost' | 'ghost-danger';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  disabled?: boolean;
  type?: 'button' | 'submit' | 'reset';
}

const props = withDefaults(defineProps<ButtonProps>(), {
  variant: 'primary',
  size: 'md',
  isLoading: false,
  disabled: false,
  type: 'button',
});

const variants: Record<string, string> = {
  primary: 'bg-brand-primary text-white shadow-sm shadow-brand-secondary hover:bg-brand-primary-hover hover:cursor-pointer',
  secondary: 'bg-gray-200 text-gray-800 hover:bg-gray-300 focus:ring-gray-500 hover:cursor-pointer',
  danger: 'bg-red-600 text-white hover:bg-red-700 focus:ring-red-500 hover:cursor-pointer',
  ghost: 'bg-transparent text-brand-primary border border-brand-primary hover:bg-brand-primary/10 hover:cursor-pointer',
  'ghost-danger': 'bg-transparent text-red-600 border border-red-200 hover:bg-red-50 hover:cursor-pointer hover:border-red-600',
};

const sizes: Record<string, string> = {
  sm: 'px-3 py-1 text-xs min-h-9',
  md: 'px-4 py-2 text-sm min-h-11',
  lg: 'px-5 py-2.5 text-base min-h-13',
};

const buttonClasses = computed(() => {
  return [
    'inline-flex items-center justify-center font-semibold rounded-md transition-all disabled:opacity-50 disabled:cursor-not-allowed',
    variants[props.variant as string],
    sizes[props.size as string],
  ];
});
</script>

<template>
  <button :type="type" :class="buttonClasses" :disabled="isLoading || disabled">
    <slot>Enviar</slot>
    <svg
      v-if="isLoading"
      class="animate-spin ml-2 -mr-1 h-4 w-4 text-current"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle
        class="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        stroke-width="4"
      ></circle>
      <path
        class="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      ></path>
    </svg>
  </button>
</template>
