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
     * Repare na diferença de tratamento em relação ao pai: sub-item sem módulo
     * aparece COM CADEADO, não some. O pai some porque anunciar um módulo que a
     * loja não comprou não ajuda ninguém; aqui a loja já está dentro do módulo,
     * e o item travado é justamente onde o upgrade se vende. Sumir com ele só
     * geraria "o sistema perdeu uma tela" no suporte.
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
     * funcionario pode fazer, modulo diz o que a LOJA comprou. Sem modulo o
     * item nao aparece para ninguem, nem para o dono.
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
