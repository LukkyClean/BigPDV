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
}

export interface SidebarSection {
    title: sidebarTitles;
    options: SidebarOption[];
}
