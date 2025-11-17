package com.llmquality.baseline.mapper;

import com.llmquality.baseline.dto.product.ProductRequest;
import com.llmquality.baseline.dto.product.ProductResponse;
import com.llmquality.baseline.entity.Product;
import org.mapstruct.*;


/**
 * MapStruct mapper for converting between {@link Product} entities and product DTOs.
 *
 * <p>Maps {@link ProductRequest} to {@link Product} for creation and partial updates,
 * and converts {@link Product} entities to {@link ProductResponse} for API responses.</p>
 *
 * <p>All mappings are generated at compile time and injected as Spring beans
 * (component model = "spring").</p>
 */
@Mapper(componentModel = "spring")
public interface ProductMapper {

    /**
     * Converts a {@link ProductRequest} to a new {@link Product} entity.
     *
     * <p>Ignores {@code id} (database-generated) and {@code orderItems} (not needed on creation).</p>
     *
     * @param request the product creation request
     * @return a new {@link Product} entity ready for persistence
     */
    @Mapping(target = "id", ignore = true)
    @Mapping(target = "orderItems", ignore = true)
    Product toProductEntity(ProductRequest request);

    /**
     * Converts a {@link Product} entity to a {@link ProductResponse}.
     *
     * <p>Field names match directly, so no explicit mappings are required.</p>
     *
     * @param product the persisted product entity
     * @return the API response DTO
     */
    ProductResponse toProductResponse(Product product);

    /**
     * Partially updates an existing {@link Product} entity from a {@link ProductRequest}.
     *
     * <p>Only non-null fields from the request are applied. {@code id} and {@code orderItems}
     * are ignored to prevent accidental overwrites.</p>
     *
     * @param request the update request (may contain partial data)
     * @param product the existing entity to update (target)
     * @return the updated entity
     */
    @Mapping(target = "id", ignore = true)
    @Mapping(target = "orderItems", ignore = true)
    @Mapping(target = "title", source = "title", nullValuePropertyMappingStrategy = NullValuePropertyMappingStrategy.IGNORE)
    @Mapping(target = "description", source = "description", nullValuePropertyMappingStrategy = NullValuePropertyMappingStrategy.IGNORE)
    @Mapping(target = "price", source = "price", nullValuePropertyMappingStrategy = NullValuePropertyMappingStrategy.IGNORE)
    @Mapping(target = "stock", source = "stock", nullValuePropertyMappingStrategy = NullValuePropertyMappingStrategy.IGNORE)
    Product updateEntityFromRequest(ProductRequest request, @MappingTarget Product product);
}
