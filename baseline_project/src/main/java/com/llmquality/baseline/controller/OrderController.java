package com.llmquality.baseline.controller;

import com.llmquality.baseline.dto.order.OrderRequest;
import com.llmquality.baseline.dto.order.OrderResponse;
import com.llmquality.baseline.dto.user.PagedResponse;
import com.llmquality.baseline.service.interfaces.OrderService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Pageable;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import static com.llmquality.baseline.dto.order.validation.OrderValidationGroups.*;


@RestController
@RequestMapping("${api.base-path}/orders")
@Validated
public class OrderController {

    private final OrderService orderService;


    @Autowired
    public OrderController(final OrderService orderService) {
        this.orderService = orderService;
    }

    @GetMapping
    @PreAuthorize("hasRole('ROLE_ADMIN') or hasRole('ROLE_USER')")
    public PagedResponse<OrderResponse> listAll(Pageable pageable) {
        return orderService.listAll(pageable);
    }

    @GetMapping("/{id}")
    @PreAuthorize("hasRole('ROLE_ADMIN') or @orderSecurityService.isOrderOwner(#id)")
    public OrderResponse getById(@PathVariable Long id) {
        return orderService.getById(id);
    }

    @PostMapping
    @PreAuthorize("hasRole('ROLE_USER') or hasRole('ROLE_ADMIN')")
    public OrderResponse create(@RequestBody @Validated(Create.class) OrderRequest orderRequest) {
        return orderService.save(orderRequest);
    }

    @DeleteMapping("/{id}")
    @PreAuthorize("hasRole('ROLE_ADMIN')")
    public void delete(@PathVariable Long id) {
        orderService.delete(id);
    }
}