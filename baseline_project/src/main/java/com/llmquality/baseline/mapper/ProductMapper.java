package com.llmquality.baseline.mapper;

import com.llmquality.baseline.dto.product.ProductRequest;
import com.llmquality.baseline.dto.product.ProductResponse;
import com.llmquality.baseline.entity.Product;
import org.mapstruct.*;

/**
 * Mapper interface for converting between database entity {@link Product} and Product DTOs.
 */
@Mapper(componentModel = "spring")
public interface ProductMapper {

    @Mapping(target = "id", ignore = true)
    @Mapping(target = "orderItems", ignore = true)
    Product toProductEntity(ProductRequest request);

    ProductResponse toProductResponse(Product product);

    @Mapping(target = "id", ignore = true)
    @Mapping(target = "orderItems", ignore = true)
    @Mapping(target = "title", source = "title", nullValuePropertyMappingStrategy = NullValuePropertyMappingStrategy.IGNORE)
    @Mapping(target = "description", source = "description", nullValuePropertyMappingStrategy = NullValuePropertyMappingStrategy.IGNORE)
    @Mapping(target = "price", source = "price", nullValuePropertyMappingStrategy = NullValuePropertyMappingStrategy.IGNORE)
    @Mapping(target = "stock", source = "stock", nullValuePropertyMappingStrategy = NullValuePropertyMappingStrategy.IGNORE)
    Product updateEntityFromRequest(ProductRequest request, @MappingTarget Product product);
}