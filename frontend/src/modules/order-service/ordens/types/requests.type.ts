import { OrderServiceUpdateDataType, OrderServiceReadyDataType, OrderServiceCancelDataType } from "../schemas/orderServiceMutate.schema";

import { OsItemCreateSchemaDataType, OsItemUpdateSchemaDataType } from "../schemas/relationship/osItem.schema";
import { OsObjetoUpdateSchemaDataType } from "../schemas/relationship/osObjeto.schema";

export interface OsItemCreateRequest {
    osNumber: string,
    osItem: OsItemCreateSchemaDataType
}

export interface OsItemUpdateRequest {
    osNumber: string,
    osItemId: number,
    updatedItem: OsItemUpdateSchemaDataType
}

export interface OrderServiceUpdateRequest {
    osNumber: string,
    updatedOS: OrderServiceUpdateDataType
}

export interface OsObjetoUpdateRequest {
    osNumber: string,
    updatedObjeto: OsObjetoUpdateSchemaDataType
}

export interface OsReadyUpdateRequest {
    osNumber: string,
    readyOs: OrderServiceReadyDataType
}

export interface OsCancelUpdateRequest {
    osNumber: string,
    cancelOs: OrderServiceCancelDataType
}

export interface OsDeleteItem {
    osNumber: string,
    itemOsId: number
}

export interface OsFotoUploadRequest {
    osNumber: string,
    imageFile: File
}

export interface OsFotoDeleteRequest {
    osNumber: string,
    fotoId: number
}