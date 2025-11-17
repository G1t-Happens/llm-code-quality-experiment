package com.llmquality.baseline.mapper;

import com.llmquality.baseline.dto.order.OrderItemRequest;
import com.llmquality.baseline.dto.order.OrderItemResponse;
import com.llmquality.baseline.entity.OrderItem;
import org.mapstruct.Mapper;
import org.mapstruct.Mapping;


@Mapper(componentModel = "spring")
public interface OrderItemMapper {

    OrderItem toEntity(OrderItemRequest request);

    @Mapping(target = "productTitle", source = "product.title")
    OrderItemResponse toResponse(OrderItem item);
}