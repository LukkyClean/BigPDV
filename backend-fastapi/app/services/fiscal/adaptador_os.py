# ---------------------------------------------------------------------------
# ARQUIVO: app/services/fiscal/adaptador_os.py
# DESCRIÇÃO: Apresenta uma Ordem de Serviço com a forma de uma Venda, para que
#            o motor fiscal continue tendo UMA implementação só.
#
# Por que adaptar em vez de duplicar: o caminho da venda (resolver de alíquotas,
# rateio, montagem de itens, fechamento de pagamentos) tem 1280 testes atrás
# dele e regras que só se aprende apanhando — a Rejeição 767, o CST 49 do
# Simples, o GTIN que não é GTIN. Uma segunda implementação para OS começaria
# concordando e divergiria na primeira correção feita só de um lado. Foi
# exatamente o que aconteceu com `verificar_emitente`, que tinha duas cópias.
#
# O QUE ENTRA NA NF-e DE UMA OS: só os itens de PRODUTO, e só os que não foram
# reprovados. Mão de obra é serviço e pede NFS-e (municipal), que não existe
# aqui. É a mesma regra que `validators.verificar_itens_os_nfe` já aplica no
# gate — o adaptador não inventa recorte, ele obedece o que o gate valida.
# ---------------------------------------------------------------------------

from typing import Optional

from app.core.enum import OrdemServicoItemAprovacao, OrdemServicoItemTipo
from app.db.models.ordem_servico import OrdemServico


class ItemOSComoItemVenda:
    """Um item de produto da OS falando o vocabulário de `ProdutoVenda`.

    O motor lê `produto`, `quantidade`, `valor_unitario`, `subtotal` e
    `desconto`. A OS guarda os mesmos números com outros nomes (`produtos` no
    plural, `valor_total` no lugar de `subtotal`) e sem desconto por item.
    """

    __slots__ = (
        "produto", "produto_id", "quantidade", "valor_unitario",
        "subtotal", "desconto", "descricao_avulsa", "item_os",
    )

    def __init__(self, item, desconto_rateado: int):
        self.item_os = item
        self.produto = item.produtos           # na OS o relacionamento é plural
        self.produto_id = item.produto_id
        # Fracionária de propósito: a serigrafia vende 2,5 kg de tinta.
        self.quantidade = item.quantidade
        self.valor_unitario = item.valor_unitario
        self.subtotal = item.valor_total
        self.desconto = desconto_rateado
        self.descricao_avulsa = item.nome


class PagamentoOSComoPagamentoVenda:
    """Pagamento da OS reduzido à parcela que cabe aos produtos.

    O motor só lê `forma_pagamento` e `valor`.
    """

    __slots__ = ("forma_pagamento", "valor", "pagamento_os")

    def __init__(self, pagamento, valor_proporcional: int):
        self.pagamento_os = pagamento
        self.forma_pagamento = pagamento.forma_pagamento
        self.valor = valor_proporcional


class OSComoVenda:
    """A OS com a superfície que o motor fiscal espera de uma `Venda`."""

    __slots__ = (
        "itens", "cliente", "pagamentos", "total", "troco",
        "entrega", "acrescimo", "nota_fiscal", "numero_venda", "os",
    )

    def __init__(self, os_obj: OrdemServico):
        self.os = os_obj

        itens_produto = itens_de_produto(os_obj)
        base_produtos = sum(i.valor_total for i in itens_produto)

        descontos = _ratear(_desconto_dos_produtos(os_obj, base_produtos), itens_produto)
        self.itens = [
            ItemOSComoItemVenda(item, desconto)
            for item, desconto in zip(itens_produto, descontos)
        ]

        # O total da NF-e é o dos PRODUTOS, não o da OS.
        self.total = base_produtos - sum(descontos)

        # Frete e acréscimo ficam de fora: são da OS inteira, e trazer uma
        # fatia deles mexeria na base de ICMS de uma nota que cobre só as
        # peças. Quando a OS tiver frete de peça, ele entra aqui.
        self.entrega = 0
        self.acrescimo = 0

        # Troco não existe na OS. Zero mantém a equação de fechamento
        # (Σ pagamentos − troco == total) legível.
        self.troco = 0

        self.pagamentos = _pagamentos_proporcionais(os_obj, self.total)

        self.cliente = getattr(os_obj.objeto, "cliente", None) if os_obj.objeto else None
        self.nota_fiscal = os_obj.nota_fiscal
        # Só para mensagens de erro; a numeração fiscal é reservada à parte.
        self.numero_venda = os_obj.numero_os


# ---------------------------------------------------------------------------
# Regras
# ---------------------------------------------------------------------------

def itens_de_produto(os_obj: OrdemServico) -> list:
    """Itens que entram na NF-e: produto, e não reprovados.

    Mesmo filtro de `validators.verificar_itens_os_nfe`. Se os dois divergirem,
    o gate aprova uma nota diferente da que sai — por isso a regra vive escrita
    uma vez e é citada nos dois lugares.
    """
    return [
        i for i in os_obj.itens
        if i.tipo == OrdemServicoItemTipo.PRODUTO
        and i.status_aprovacao != OrdemServicoItemAprovacao.REPROVADO
    ]


def _desconto_dos_produtos(os_obj: OrdemServico, base_produtos: int) -> int:
    """A parte do desconto da OS que cabe aos produtos.

    A OS desconta no total (peças + mão de obra); a NF-e cobre só as peças.
    Levar o desconto inteiro para a nota subfaturaria; ignorá-lo faria a nota
    valer mais do que o cliente pagou por elas. A fatia proporcional é a única
    leitura que fecha dos dois lados.
    """
    desconto = os_obj.desconto or 0
    bruto = os_obj.valor_bruto or 0
    if desconto <= 0 or bruto <= 0 or base_produtos <= 0:
        return 0
    return min(base_produtos, round(desconto * base_produtos / bruto))


def _ratear(total: int, itens: list) -> list[int]:
    """Distribui `total` entre os itens em proporção ao valor de cada um.

    A sobra de arredondamento vai para o item de maior valor, como no
    `tax_engine/rateio.py` — assim a soma das partes é exatamente o total, e o
    centavo perdido não some da nota.
    """
    if total <= 0 or not itens:
        return [0] * len(itens)

    base = sum(i.valor_total for i in itens)
    if base <= 0:
        return [0] * len(itens)

    partes = [round(total * i.valor_total / base) for i in itens]

    sobra = total - sum(partes)
    if sobra:
        maior = max(range(len(itens)), key=lambda k: itens[k].valor_total)
        partes[maior] += sobra

    return partes


def _pagamentos_proporcionais(os_obj: OrdemServico, total_nota: int) -> list:
    """Pagamentos reduzidos à fatia que corresponde aos produtos.

    A SEFAZ audita `Σ pagamentos − troco == total da nota` (Rejeição 767). Os
    pagamentos de uma OS cobrem peças E mão de obra, então mandá-los inteiros
    numa nota que cobre só as peças derruba a emissão — e mandar um pagamento
    único inventado apagaria as formas que o cliente de fato usou.

    Proporcional preserva as formas (dinheiro, cartão, PIX) e fecha a conta. A
    sobra de arredondamento vai para o maior pagamento.
    """
    pagamentos = [p for p in (os_obj.pagamentos or []) if p.forma_pagamento]
    if not pagamentos or total_nota <= 0:
        return []

    base = sum(p.valor for p in pagamentos)
    if base <= 0:
        return []

    valores = [round(total_nota * p.valor / base) for p in pagamentos]

    sobra = total_nota - sum(valores)
    if sobra:
        maior = max(range(len(pagamentos)), key=lambda k: pagamentos[k].valor)
        valores[maior] += sobra

    return [
        PagamentoOSComoPagamentoVenda(p, v)
        for p, v in zip(pagamentos, valores)
        if v > 0
    ]


def adaptar(os_obj: OrdemServico) -> OSComoVenda:
    """Ponto de entrada — a OS vista como venda, para o motor fiscal."""
    return OSComoVenda(os_obj)


def uf_do_cliente(os_obj: OrdemServico) -> Optional[str]:
    """UF do primeiro endereço do cliente da OS, se houver."""
    cliente = getattr(os_obj.objeto, "cliente", None) if os_obj.objeto else None
    enderecos = getattr(cliente, "endereco", None) if cliente else None
    if not enderecos:
        return None
    estado = enderecos[0].estado
    return str(estado.value) if hasattr(estado, "value") else (str(estado) or None)
