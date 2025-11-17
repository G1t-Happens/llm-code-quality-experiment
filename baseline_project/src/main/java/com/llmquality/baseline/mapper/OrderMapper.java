package com.llmquality.baseline.mapper;


import com.llmquality.baseline.dto.order.OrderRequest;
import com.llmquality.baseline.dto.order.OrderResponse;
import com.llmquality.baseline.entity.Order;
import org.mapstruct.Mapper;


/**
 * Mapper interface for converting between database entity {@link Order} and Order DTOs.
 */
@Mapper(componentModel = "spring", uses = OrderItemMapper.class)
public interface OrderMapper {

    Order toEntity(OrderRequest request);

    OrderResponse toResponse(Order order);
}
