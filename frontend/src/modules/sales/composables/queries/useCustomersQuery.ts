import { computed, unref, type MaybeRef } from "vue";

import { useQuery } from "@tanstack/vue-query";

import { customerService } from "../../api.service";
import { customerKeys } from "../../query.keys";
import { REFETCH_REALTIME } from "@/core/config/queryIntervals";

import { CustomerSimpleRead } from "../../schemas/customers.schema";

export function useCustomersQuery(term: MaybeRef<string | null | undefined>) {
    return useQuery<CustomerSimpleRead>({
        queryKey: computed(() => 
            !!unref(term)
              ? customerKeys.search(unref(term)!)
              : [...customerKeys.all, 'venda-busca', 'empty']
        ),
        queryFn: () => customerService.searchCustomers(unref(term)!),
        staleTime: 1000 * 30, // auto-complete: igual ao de produto, ao lado
        refetchInterval: REFETCH_REALTIME,
    })
}