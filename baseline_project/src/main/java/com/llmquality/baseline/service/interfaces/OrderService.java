package com.llmquality.baseline.service.interfaces;

import com.llmquality.baseline.dto.order.OrderRequest;
import com.llmquality.baseline.dto.order.OrderResponse;
import com.llmquality.baseline.entity.Order;


/**
 * Service interface for managing {@link Order} entities and performing
 * user-related operations.
 * <p>
 * Extends {@link CRUDable} to provide standard Create, Read, Update,
 * and Delete operations for {@link Order} objects.
 * </p>
 */
public interface OrderService extends CRUDable<OrderRequest, OrderResponse> {

}