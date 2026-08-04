import { useQuery } from '@tanstack/vue-query';

import {
  getEmployeesAll,
  getCustomersAll,
} from '../../../services/relationship/osRelationshipGet.service';

import {
  OS_CUSTOMER_QUERY_KEY,
  OS_CUSTOMER_QUERY_STALE_TIME,
  OS_EMPLOYEE_QUERY_KEY,
  OS_EMPLOYEE_QUERY_STALE_TIME,
  ORDER_SERVICE_REFETCH_INTERVAL,
} from '../../../constants/core.constant';

export function useOsCustomersGet() {
  return useQuery({
    queryKey: OS_CUSTOMER_QUERY_KEY,
    queryFn: getCustomersAll,
    staleTime: OS_CUSTOMER_QUERY_STALE_TIME,
    refetchInterval: ORDER_SERVICE_REFETCH_INTERVAL,
  });
}

export function useOsEmployeesGet() {
  return useQuery({
    queryKey: [OS_EMPLOYEE_QUERY_KEY],
    queryFn: getEmployeesAll,
    staleTime: OS_EMPLOYEE_QUERY_STALE_TIME,
    refetchInterval: ORDER_SERVICE_REFETCH_INTERVAL,
  });
}
