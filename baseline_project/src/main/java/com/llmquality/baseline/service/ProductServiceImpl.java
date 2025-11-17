package com.llmquality.baseline.service;

import com.llmquality.baseline.dto.product.*;
import com.llmquality.baseline.dto.user.PagedResponse;
import com.llmquality.baseline.entity.Product;
import com.llmquality.baseline.exception.ResourceNotFoundException;
import com.llmquality.baseline.mapper.ProductMapper;
import com.llmquality.baseline.repository.ProductRepository;
import com.llmquality.baseline.service.interfaces.ProductService;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;


@Service
public class ProductServiceImpl implements ProductService {

    private static final org.slf4j.Logger LOG = LoggerFactory.getLogger(ProductServiceImpl.class);

    private static final String PRODUCT = "Product";

    private final ProductRepository productRepository;

    private final ProductMapper productMapper;

    @Autowired
    public ProductServiceImpl(final ProductRepository productRepository, final ProductMapper productMapper) {
        this.productRepository = productRepository;
        this.productMapper = productMapper;
    }

    @Override
    public PagedResponse<ProductResponse> listAll(final Pageable pageable) {
        LOG.debug("--> listAll, page={}, size={}", pageable.getPageNumber(), pageable.getPageSize());
        final Page<ProductResponse> page = productRepository.findAll(pageable).map(productMapper::toProductResponse);
        LOG.debug("<-- listAll, total elements={}, total pages={}", page.getTotalElements(), page.getTotalPages());
        return PagedResponse.fromPage(page);
    }

    @Override
    public ProductResponse getById(final Long id) {
        LOG.debug("--> getById product {}", id);
        final Product product = productRepository.findById(id)
                .orElseThrow(() -> {
                    LOG.error("<-- getById, Product with ID {} not found", id);
                    return new ResourceNotFoundException(PRODUCT, "id", id);
                });

        final ProductResponse productResponse = productMapper.toProductResponse(product);
        LOG.debug("<-- getById, product found: {}", productResponse.id());
        return productResponse;
    }

    @Override
    public ProductResponse save(final ProductRequest productRequest) {
        LOG.debug("--> save product with title: {}", productRequest.title());
        final Product productEntity = productMapper.toProductEntity(productRequest);
        final Product savedProductEntity = productRepository.save(productEntity);
        final ProductResponse productResponse = productMapper.toProductResponse(savedProductEntity);
        LOG.debug("<-- save, product saved with id: {}", productResponse.id());
        return productResponse;
    }

    @Override
    public ProductResponse update(final Long id, final ProductRequest request) {
        LOG.debug("--> update product {}", id);
        final Product product = productRepository.findById(id)
                .orElseThrow(() -> {
                    LOG.error("<-- update, product with ID {} not found", id);
                    return new ResourceNotFoundException(PRODUCT, "id", id);
                });
        final Product updatedProductEntity = productMapper.updateEntityFromRequest(request, product);
        final Product savedProductEntity = productRepository.save(updatedProductEntity);
        final ProductResponse productResponse = productMapper.toProductResponse(savedProductEntity);
        LOG.debug("<-- update, product found: {}", productResponse.id());
        return productResponse;
    }

    @Override
    public void delete(Long id) {
        LOG.debug("--> delete, id: {}", id);

        final Product existingProductEntity = productRepository.findById(id)
                .orElseThrow(() -> {
                    LOG.error("<-- delete, product with ID {} not found", id);
                    return new ResourceNotFoundException(PRODUCT, "id", id);
                });

        productRepository.delete(existingProductEntity);
        LOG.debug("<-- delete, product deleted with id: {}", id);
    }
}