package com.llmquality.baseline.mapper;

import com.llmquality.baseline.dto.order.OrderItemRequest;
import com.llmquality.baseline.dto.order.OrderItemResponse;
import com.llmquality.baseline.entity.OrderItem;
import org.mapstruct.Mapper;
import org.mapstruct.Mapping;


/**
 * MapStruct mapper for converting between {@link OrderItem} entities and order item DTOs.
 *
 * <p>Responsible for mapping individual line items when creating an order
 * ({@link OrderItemRequest} to {@link OrderItem}) and exposing detailed item information
 * in responses ({@link OrderItem} to {@link OrderItemResponse}).</p>
 *
 * <p>Mappings are generated at compile time and injected as a Spring bean.</p>
 */
@Mapper(componentModel = "spring")
public interface OrderItemMapper {

    /**
     * Converts an {@link OrderItemRequest} to a new {@link OrderItem} entity.
     *
     * <p>Used during order creation. The product reference and calculated fields
     * (e.g., unit price, subtotal) are set separately in the service layer.</p>
     *
     * @param request the requested product and quantity
     * @return a new {@link OrderItem} entity
     */
    OrderItem toOrderItemEntity(OrderItemRequest request);

    /**
     * Converts a persisted {@link OrderItem} entity to an {@link OrderItemResponse}.
     *
     * <p>Includes the associated product's ID and title for display purposes,
     * along with quantity, unit price, and calculated subtotal.</p>
     *
     * @param item the persisted order item entity
     * @return the response DTO containing full item details
     */
    @Mapping(target = "productId", source = "product.id")
    @Mapping(target = "productTitle", source = "product.title")
    OrderItemResponse toOrderItemResponse(OrderItem item);
}
