<script setup lang="ts">
/**
 * @section RedeConexao
 * @description Configurações › Rede e Conexão. Mostra o papel da máquina, o
 *   endereço da API em uso, os IPs locais e o estado do serviço local, com ações de
 *   reiniciar/reparar (servidor) ou buscar servidor (terminal). Só leitura — não
 *   participa do "Salvar" do modal.
 */
import DiagnosticoConexao from '@/shared/components/DiagnosticoConexao.vue'
</script>

<template>
  <div class="flex flex-col gap-6">
    <div>
      <h3 class="text-base font-bold text-zinc-900">Rede e Conexão</h3>
      <p class="text-sm text-zinc-500 mt-0.5">
        Como este computador se comunica com o servidor do StartBig na rede local
      </p>
    </div>

    <DiagnosticoConexao />

    <div class="bg-amber-50 border border-amber-100 rounded-xl p-4 text-xs text-amber-800 space-y-1">
      <p class="font-semibold">Recomendações para o computador servidor</p>
      <ul class="list-disc pl-4 space-y-0.5">
        <li>Configure um IP fixo (ou reserva DHCP) no roteador — sem isso o endereço pode mudar ao ligar a máquina.</li>
        <li>Desative a "Inicialização Rápida" do Windows para o serviço subir corretamente após desligar.</li>
        <li>Para alterar o tipo de máquina (servidor/terminal), entre em contato com o suporte técnico.</li>
      </ul>
    </div>
  </div>
</template>
