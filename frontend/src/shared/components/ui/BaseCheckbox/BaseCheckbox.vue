<script setup lang="ts">
/**
 * @component BaseCheckbox
 * @description Componente de checkbox reutilizável com suporte a v-model,
 * labels e estados de erro.
 */

interface CheckboxProps {
  label?: string;
  disabled?: boolean;
  id?: string;
}

const props = defineProps<CheckboxProps>();

const uniqueId = props.id || `checkbox-${Math.random().toString(36).slice(2, 7)}`;
const value = defineModel<boolean>({default: false});
</script>

<template>
  <div class="flex items-center gap-1.5">
    <input
      v-model="value"
      :id="uniqueId"
      type="checkbox"
      :disabled="disabled"
      class="w-3.5 h-3.5 border-gray-300 rounded accent-brand-primary text-brand-primary focus:ring-brand-primary focus:ring-1 cursor-pointer disabled:cursor-not-allowed disabled:opacity-50"
    />
    <label
      v-if="label"
      :for="uniqueId"
      class="text-xs text-gray-600 cursor-pointer select-none"
      :class="{ 'opacity-50 cursor-not-allowed': disabled }"
    >
      {{ label }}
    </label>
  </div>
</template>
