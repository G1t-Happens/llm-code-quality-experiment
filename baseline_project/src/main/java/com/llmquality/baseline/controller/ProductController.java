package com.llmquality.baseline.controller;

import com.llmquality.baseline.dto.product.ProductRequest;
import com.llmquality.baseline.dto.product.ProductResponse;
import com.llmquality.baseline.dto.user.PagedResponse;
import com.llmquality.baseline.service.interfaces.ProductService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Pageable;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import static com.llmquality.baseline.dto.product.validation.ProductValidationGroups.*;


@RestController
@RequestMapping("${api.base-path}/products")
@Validated
public class ProductController {

    private final ProductService productService;


    @Autowired
    public ProductController(final ProductService productService) {
        this.productService = productService;
    }

    @GetMapping
    public PagedResponse<ProductResponse> listAll(Pageable pageable) {
        return productService.listAll(pageable);
    }

    @GetMapping("/{id}")
    public ProductResponse getById(@PathVariable Long id) {
        return productService.getById(id);
    }

    @PostMapping
    @PreAuthorize("hasRole('ROLE_ADMIN')")
    public ProductResponse create(@RequestBody @Validated(Create.class) ProductRequest req) {
        return productService.save(req);
    }

    @PatchMapping("/{id}")
    @PreAuthorize("hasRole('ROLE_ADMIN')")
    public ProductResponse update(@PathVariable Long id, @RequestBody @Validated(Update.class) ProductRequest req) {
        return productService.update(id, req);
    }

    @DeleteMapping("/{id}")
    @PreAuthorize("hasRole('ROLE_ADMIN')")
    public void delete(@PathVariable Long id) {
        productService.delete(id);
    }
}
