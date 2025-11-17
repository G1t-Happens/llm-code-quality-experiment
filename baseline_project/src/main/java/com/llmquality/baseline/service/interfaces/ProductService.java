package com.llmquality.baseline.service.interfaces;

import com.llmquality.baseline.dto.product.ProductRequest;
import com.llmquality.baseline.dto.product.ProductResponse;
import com.llmquality.baseline.entity.Product;


/**
 * Service interface for managing {@link Product} entities and performing
 * user-related operations.
 * <p>
 * Extends {@link CRUDable} to provide standard Create, Read, Update,
 * and Delete operations for {@link Product} objects.
 * </p>
 */
public interface ProductService extends CRUDable<ProductRequest, ProductResponse> {

}