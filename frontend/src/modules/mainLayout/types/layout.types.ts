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
}

export interface SidebarSection {
    title: sidebarTitles;
    options: SidebarOption[];
}
