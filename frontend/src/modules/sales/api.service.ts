import api from '@/api/axios';

import { parseSchema } from './parseSchema.util';

import {
  SaleCreate,
  SaleUpdate,
  SaleSearch,
  SaleList,
  SaleRead,
  SalesStatus,
  SalesStatusSchema,
  SaleReadSchema,
  SaleListSchema,
  SaleUpdateSchema,
} from './schemas/sale.schema';

import {
  ProductSaleCreate,
  ProductSaleUpdate,
  ProductAlteration,
  ProductAlterationSchema,
  ProductSaleListItem,
  ProductSaleListItemSchema,
} from './schemas/productSale.schema';

import { PaymentSaleCreate } from './schemas/paymentSale.schema';
import { CustomerSimpleRead, CustomerDiscriminatedSimpleReadSchema } from './schemas/customers.schema';

const SALE_ENDPOINT = '/vendas';

export const saleService = {
  async createSale(sale: SaleCreate): Promise<SaleRead> {
    const { data } = await api.post<SaleRead>(SALE_ENDPOINT, sale);
    return parseSchema(SaleReadSchema, data, 'saleService.createSale.response');
  },

  async updateSale(sale_id: number, sale: SaleUpdate): Promise<SaleRead> {
    const parsedSale = parseSchema(SaleUpdateSchema, sale, 'saleService.updateSale.request');
    const { data } = await api.patch<SaleRead>(`${SALE_ENDPOINT}/${sale_id}`, parsedSale);
    return parseSchema(SaleReadSchema, data, 'saleService.updateSale.response');
  },

  async addItemInSale(sale_id: number, product: ProductSaleCreate): Promise<ProductAlteration> {
    const { data } = await api.post<ProductAlteration>(
      `${SALE_ENDPOINT}/${sale_id}/itens`,
      product,
    );
    return parseSchema(ProductAlterationSchema, data, 'saleService.addItemInSale.response');
  },

  async deleteItemInSale(sale_id: number, product_id: number): Promise<SaleRead> {
    const { data } = await api.delete<SaleRead>(`${SALE_ENDPOINT}/${sale_id}/itens/${product_id}`);
    return parseSchema(SaleReadSchema, data, 'saleService.deleteItemInSale.response');
  },

  async updateItemInSale(
    sale_id: number,
    product_id: number,
    product: ProductSaleUpdate,
  ): Promise<ProductAlteration> {
    const { data } = await api.patch<ProductAlteration>(
      `${SALE_ENDPOINT}/${sale_id}/itens/${product_id}`,
      product,
    );
    return parseSchema(ProductAlterationSchema, data, 'saleService.updateItemInSale.response');
  },

  async finishSale(sale_id: number, payments: PaymentSaleCreate[], acrescimo = 0): Promise<SaleRead> {
    const { data } = await api.post<SaleRead>(`${SALE_ENDPOINT}/${sale_id}/finalizar`, {
      pagamentos: payments,
      acrescimo,
    });
    return parseSchema(SaleReadSchema, data, 'saleService.finishSale.response');
  },

  async deleteSale(sale_id: number): Promise<void> {
    await api.delete(`${SALE_ENDPOINT}/${sale_id}`);
  },

  async cancelSale(sale_id: number, motivo: string, codigo_gerente?: string | null): Promise<SaleRead> {
    const { data } = await api.post<SaleRead>(`${SALE_ENDPOINT}/${sale_id}/cancelar`, { motivo, ...(codigo_gerente ? { codigo_gerente } : {}) });
    return parseSchema(SaleReadSchema, data, 'saleService.cancelSale.response');
  },

  async reopenSale(sale_id: number, codigo_gerente?: string | null): Promise<SaleRead> {
    const { data } = await api.post<SaleRead>(`${SALE_ENDPOINT}/${sale_id}/reabrir`, codigo_gerente ? { codigo_gerente } : {});
    return parseSchema(SaleReadSchema, data, 'saleService.reopenSale.response');
  },

  async getSale(sale_id: number): Promise<SaleRead> {
    const { data } = await api.get<SaleRead>(`${SALE_ENDPOINT}/${sale_id}`);
    return parseSchema(SaleReadSchema, data, 'saleService.getSale.response');
  },

  async listSales(query?: SaleSearch, page: number = 1): Promise<SaleList> {
    const params = {
      ...(query?.search && { search: query.search }),
      ...(query?.status && { status: query.status }),
      page : page,
    };

    const { data } = await api.get<SaleList>(`${SALE_ENDPOINT}/`, { params });
    return parseSchema(SaleListSchema, data, 'saleService.listSales.response');
  },

  async getSalesStatus(): Promise<SalesStatus> {
    const { data } = await api.get<SalesStatus>(`${SALE_ENDPOINT}/status/`);
    return parseSchema(SalesStatusSchema, data, 'saleService.getSalesStatus.response');
  },
};

export const productService = {
  async searchProducts(search: string): Promise<ProductSaleListItem> {
    const { data } = await api.get<ProductSaleListItem>(`/produtos/search`, { params: { search } });
    return parseSchema(ProductSaleListItemSchema, data, 'productService.searchProducts.response');
  }
}

export const customerService = {
  async searchCustomers(search: string): Promise<CustomerSimpleRead> {
    const { data } = await api.get<CustomerSimpleRead>(`/clientes/search`, { params: { search } });
    return parseSchema(CustomerDiscriminatedSimpleReadSchema, data, 'customerService.searchCustomers.response');
  }
}
