import { computed, unref, type MaybeRef } from 'vue';
import { useQuery } from '@tanstack/vue-query';

import { productService } from '../../api.service';
import { productKeys } from '../../query.keys';
import { REFETCH_REALTIME } from '@/core/config/queryIntervals';

import { ProductSaleListItem } from '../../schemas/productSale.schema';

export function useProductQuery(term: MaybeRef<string | null | undefined>) {
  return useQuery<ProductSaleListItem>({
    queryKey: computed(() => 
      !!unref(term)
        ? productKeys.search(unref(term)!)
        : [...productKeys.all, 'venda-busca', 'empty']
    ),
    queryFn: () => productService.searchProducts(unref(term)!),
    enabled: computed(() => !!unref(term) && unref(term)!.trim().length > 1),
    staleTime: 1000 * 30,
    refetchInterval: REFETCH_REALTIME,
  });
}
