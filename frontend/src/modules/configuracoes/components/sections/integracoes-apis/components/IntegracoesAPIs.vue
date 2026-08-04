<script setup lang="ts">
/**
 * @fileoverview Integrações e APIs.
 *
 * O bloco de Nota Fiscal Eletrônica (integração ativa, ambiente, token) foi
 * removido: era maquete, e emissão de NF-e não está no caminho deste produto nem
 * desta categoria de cliente. Tela que promete o que não vai existir gera
 * expectativa e chamado de suporte.
 *
 * O bloco de PIX permanece como espaço reservado — a chave PIX e o QR Code na
 * finalização da venda são o próximo passo, e diferente da NF-e são viáveis sem
 * integração bancária: o QR estático é montado offline a partir da chave.
 */
</script>

<template>
  <div class="flex flex-col gap-6">
    <div>
      <h3 class="text-base font-bold text-zinc-900">Integrações e APIs</h3>
      <p class="text-sm text-zinc-500 mt-0.5">Conecte o sistema com serviços externos e configure integrações</p>
    </div>

    <div class="flex flex-col gap-3">
      <p class="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">PIX</p>

      <div class="flex items-center justify-between py-3 border-b border-zinc-100">
        <div>
          <p class="text-sm font-medium text-zinc-800">Integração PIX ativa</p>
          <p class="text-xs text-zinc-500 mt-0.5">Habilita QR Code PIX na finalização da venda</p>
        </div>
        <div class="relative w-9 h-4.5 bg-zinc-200 rounded-full shrink-0">
          <span class="absolute left-0.5 top-0.5 w-3.5 h-3.5 bg-white rounded-full shadow" />
        </div>
      </div>

      <div class="flex flex-col gap-1.5">
        <label class="text-xs font-medium text-zinc-600">Chave PIX</label>
        <div class="border border-zinc-200 rounded-lg px-3 py-2.5 bg-zinc-50 text-sm text-zinc-400">
          Não configurada
        </div>
      </div>
    </div>
  </div>
</template>
