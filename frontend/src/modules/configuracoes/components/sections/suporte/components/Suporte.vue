<script setup lang="ts">
import { Headphones, Globe, Youtube, ExternalLink } from 'lucide-vue-next'
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue'
import { openUrl } from '@tauri-apps/plugin-opener'
import { LINKS } from '@/shared/config/links'

function abrirLink(url: string) {
  openUrl(url)
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <div>
      <h3 class="text-base font-bold text-zinc-900">Suporte e Ajuda</h3>
      <p class="text-sm text-zinc-500 mt-0.5">Encontre ajuda, entre em contato com o suporte e acesse recursos</p>
    </div>

    <div class="flex flex-col gap-3">
      <p class="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">Contato</p>

      <div class="flex flex-col gap-2">
        <BaseButton variant="primary" size="sm" @click="abrirLink(LINKS.whatsapp)">
          <Headphones :size="14" class="mr-2" />
          Falar com Suporte
          <ExternalLink :size="12" class="ml-auto opacity-60" />
        </BaseButton>

        <BaseButton variant="ghost" size="sm" @click="abrirLink(LINKS.site)">
          <Globe :size="14" class="mr-2" />
          Site Oficial — startbig.com.br
          <ExternalLink :size="12" class="ml-auto opacity-60" />
        </BaseButton>

        <BaseButton variant="ghost" size="sm" @click="abrirLink(LINKS.youtube)">
          <Youtube :size="14" class="mr-2" />
          Tutoriais em Vídeo
          <ExternalLink :size="12" class="ml-auto opacity-60" />
        </BaseButton>
      </div>
    </div>

    <div class="flex flex-col gap-3">
      <p class="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">Informações do Sistema</p>

      <div class="bg-zinc-50 rounded-xl p-4 flex flex-col gap-2.5">
        <div class="flex items-center justify-between">
          <span class="text-xs text-zinc-500">Versão do sistema</span>
          <span class="text-xs font-semibold text-zinc-700">1.0.0</span>
        </div>
        <div class="flex items-center justify-between">
          <span class="text-xs text-zinc-500">Última atualização</span>
          <span class="text-xs font-semibold text-zinc-700">01/06/2026</span>
        </div>
        <div class="flex items-center justify-between">
          <span class="text-xs text-zinc-500">Ambiente</span>
          <span class="text-xs font-semibold text-emerald-600">Produção</span>
        </div>
      </div>
    </div>
  </div>
</template>
