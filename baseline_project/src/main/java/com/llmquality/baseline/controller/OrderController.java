package com.llmquality.baseline.controller;

import com.llmquality.baseline.dto.order.OrderRequest;
import com.llmquality.baseline.dto.order.OrderResponse;
import com.llmquality.baseline.dto.product.validation.ProductValidationGroups;
import com.llmquality.baseline.dto.user.PagedResponse;
import com.llmquality.baseline.service.interfaces.OrderService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Pageable;
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
    public PagedResponse<OrderResponse> listAll(Pageable pageable) {
        return orderService.listAll(pageable);
    }

    @GetMapping("/{id}")
    public OrderResponse getById(@PathVariable Long id) {
        return orderService.getById(id);
    }

    @PostMapping
    public OrderResponse create(@RequestBody @Validated(Create.class) OrderRequest orderRequest) {
        return orderService.save(orderRequest);
    }

    @DeleteMapping("/{id}")
    public void delete(@PathVariable Long id) {
        orderService.delete(id);
    }
}