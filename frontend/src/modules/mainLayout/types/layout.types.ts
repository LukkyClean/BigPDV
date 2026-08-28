import type { Component } from "vue";

import { Permissions } from "@/shared/types/auth.types";

//Opcoes de menu existente
export type sidebarTitles =
    | 'MENU PRINCIPAL'
    | 'EMPRESA'

export type SidebarLabelOptions = 
    | 'Início'
    | 'Vendas'
    | 'Serviços'
    | 'Clientes'
    | 'Produtos'
    | 'Relatórios'
    | 'Estoque'
    | 'Dados da Empresa'
    | 'Gestão de Equipe'
    | 'Minha Conta'
    | 'Gestão Financeira'

/**
 * Sub-item de um menu que agrupa (ex.: Contas a Pagar dentro de Gestão
 * Financeira).
 *
 * Tem os MESMOS dois eixos de controle do item pai, e não por simetria: dentro
 * de um único módulo convivem telas de sigilo e de plano diferentes. Contas a
 * Pagar mostra a folha de pagamento e Contas a Receber não; Fluxo de Caixa é do
 * plano superior e Contas a Pagar é de todos.
 */
export interface SidebarSubItem {
    /** Nome da rota. É também o `tabId` que marca o item como ativo. */
    id: string;
    label: string;
    requiredPermission?: Permissions;
    /**
     * Módulo que este sub-item exige.
     *
     * Sem o módulo o item aparece COM CADEADO, nunca some — mesma regra do item
     * pai. Sumir viraria "o sistema perdeu uma tela" no suporte, e o item
     * travado é justamente onde o upgrade se vende.
     *
     * Num grupo os filhos podem exigir módulos DIFERENTES (Contas a Pagar é do
     * plano de entrada, Fluxo de Caixa do superior), e é por isso que a trava
     * mora aqui e não só no pai.
     */
    requiredModule?: string;
}

export interface SidebarOption {
    id: string;
    icon: Component;
    label: SidebarLabelOptions;
    requiredPermission?: Permissions;
    /**
     * Modulo contratado que este item exige (ex.: 'FINANCEIRO').
     *
     * Eixo diferente de `requiredPermission`: permissao diz o que ESTE
     * funcionario pode fazer, modulo diz o que a LOJA comprou. Sem o modulo o
     * item aparece TRAVADO, com cadeado -- nao some, nem para o dono. Sumir
     * vira chamado de suporte com "o sistema perdeu uma tela"; o cadeado diz a
     * verdade e e onde o upgrade se vende. Mesma razao que o backend ja da em
     * core/modulos.py para responder 403 e nao 404.
     *
     * Em item que tem `children` a trava e ignorada: quem carrega o cadeado sao
     * os filhos, cada um com o seu modulo.
     */
    requiredModule?: string;
    /**
     * Sub-itens. Presente = o item vira grupo que expande e deixa de navegar
     * por conta própria; quem navega são os filhos.
     */
    children?: SidebarSubItem[];
}

export interface SidebarSection {
    title: sidebarTitles;
    options: SidebarOption[];
}
