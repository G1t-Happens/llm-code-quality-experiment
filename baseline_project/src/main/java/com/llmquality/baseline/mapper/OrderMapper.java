package com.llmquality.baseline.mapper;

import com.llmquality.baseline.dto.order.OrderRequest;
import com.llmquality.baseline.dto.order.OrderResponse;
import com.llmquality.baseline.entity.Order;
import org.mapstruct.Mapper;
import org.mapstruct.Mapping;


/**
 * MapStruct mapper for converting between {@link Order} entities and order DTOs.
 *
 * <p>Handles mapping from {@link OrderRequest} to {@link Order} during creation
 * and from persisted {@link Order} entities to {@link OrderResponse} for API responses.</p>
 *
 * <p>Uses {@link OrderItemMapper} for converting order items. All mappings are
 * generated at compile time and registered as Spring beans.</p>
 */
@Mapper(componentModel = "spring", uses = OrderItemMapper.class)
public interface OrderMapper {

    /**
     * Maps an {@link OrderRequest} to a new {@link Order} entity.
     *
     * <p>Used when creating a new order. The inverse mapping (entity to request)
     * is intentionally not provided as orders are immutable after creation.</p>
     *
     * @param request the order creation request containing items
     * @return a new {@link Order} entity ready for persistence
     */
    Order toEntity(OrderRequest request);

    /**
     * Converts a persisted {@link Order} entity to an {@link OrderResponse}.
     *
     * <p>Maps the associated user's ID to {@code userId} and includes fully mapped
     * order items via {@link OrderItemMapper}.</p>
     *
     * @param order the persisted order entity
     * @return the API response DTO with complete order details
     */
    @Mapping(target = "userId", source = "user.id")
    OrderResponse toResponse(Order order);
}
