import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import type { OrderServiceReadDataType } from '@/modules/order-service/ordens/schemas/orderServiceQuery.schema'
import type { Comunicado } from '@/modules/mainLayout/services/comunicado.service'
import type { RevisaoPendente } from '@/modules/order-service/revisoes/services/revisao.service'

const STORAGE_KEY = 'notif_os_vistos'
// Revisão é identificada pelo VEÍCULO (objeto_id) e OS pelo id da OS. Guardar
// os dois no mesmo conjunto faria um id colidir com o outro e sumir um aviso
// que nunca foi lido — por isso as chaves são separadas.
const STORAGE_KEY_REVISOES = 'notif_revisoes_vistas'

function carregarVistos(chave = STORAGE_KEY): Set<number> {
  try {
    const raw = localStorage.getItem(chave)
    return raw ? new Set<number>(JSON.parse(raw)) : new Set()
  } catch {
    return new Set()
  }
}

export const useNotificacoesStore = defineStore('notificacoes', () => {
  const osAbandono = ref<OrderServiceReadDataType[]>([])
  const osAtrasadas = ref<OrderServiceReadDataType[]>([])
  const comunicados = ref<Comunicado[]>([])
  const revisoes = ref<RevisaoPendente[]>([])
  const osVistos = ref<Set<number>>(carregarVistos())
  const revisoesVistas = ref<Set<number>>(carregarVistos(STORAGE_KEY_REVISOES))

  watch(osVistos, (val) => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify([...val]))
  })

  watch(revisoesVistas, (val) => {
    localStorage.setItem(STORAGE_KEY_REVISOES, JSON.stringify([...val]))
  })

  const totalNaoLidas = computed(() => {
    const alertas = [
      ...osAbandono.value,
      ...osAtrasadas.value,
    ].filter(os => !osVistos.value.has(os.id)).length
    const avisos = comunicados.value.filter(c => !c.lido).length
    const revisoesNaoVistas = revisoes.value.filter(
      r => !revisoesVistas.value.has(r.objeto_id),
    ).length
    return alertas + avisos + revisoesNaoVistas
  })

  const temOsNaoVistas = computed(() =>
    osAbandono.value.some(os => !osVistos.value.has(os.id)) ||
    osAtrasadas.value.some(os => !osVistos.value.has(os.id)) ||
    revisoes.value.some(r => !revisoesVistas.value.has(r.objeto_id))
  )

  function setOsAbandono(lista: OrderServiceReadDataType[]) {
    osAbandono.value = lista
  }

  function setOsAtrasadas(lista: OrderServiceReadDataType[]) {
    osAtrasadas.value = lista
  }

  function setRevisoes(lista: RevisaoPendente[]) {
    revisoes.value = lista
  }

  /** Marca uma revisão como avisada — o clique serve só para dar ciência. */
  function marcarRevisaoVista(objetoId: number) {
    const novos = new Set(revisoesVistas.value)
    novos.add(objetoId)
    revisoesVistas.value = novos
  }

  function setComunicados(lista: Comunicado[]) {
    comunicados.value = lista
  }

  function marcarComunicadoLido(id: number) {
    const c = comunicados.value.find(x => x.id === id)
    if (c) c.lido = true
  }

  function adicionarComunicado(c: Comunicado) {
    comunicados.value.unshift(c)
  }

  function marcarOsVistas() {
    const novos = new Set(osVistos.value)
    osAbandono.value.forEach(os => novos.add(os.id))
    osAtrasadas.value.forEach(os => novos.add(os.id))
    osVistos.value = novos

    const novasRevisoes = new Set(revisoesVistas.value)
    revisoes.value.forEach(r => novasRevisoes.add(r.objeto_id))
    revisoesVistas.value = novasRevisoes
  }

  function resetar() {
    osAbandono.value = []
    osAtrasadas.value = []
    comunicados.value = []
    revisoes.value = []
    osVistos.value = new Set()
    revisoesVistas.value = new Set()
    localStorage.removeItem(STORAGE_KEY)
    localStorage.removeItem(STORAGE_KEY_REVISOES)
  }

  return {
    osAbandono,
    osAtrasadas,
    comunicados,
    revisoes,
    osVistos,
    revisoesVistas,
    totalNaoLidas,
    temOsNaoVistas,
    setOsAbandono,
    setOsAtrasadas,
    setComunicados,
    setRevisoes,
    marcarRevisaoVista,
    marcarComunicadoLido,
    adicionarComunicado,
    marcarOsVistas,
    resetar,
  }
})
