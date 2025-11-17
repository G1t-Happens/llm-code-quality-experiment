package com.llmquality.baseline.service;

import com.llmquality.baseline.dto.order.*;
import com.llmquality.baseline.dto.user.PagedResponse;
import com.llmquality.baseline.entity.*;
import com.llmquality.baseline.enums.OrderStatus;
import com.llmquality.baseline.exception.ResourceNotFoundException;
import com.llmquality.baseline.mapper.OrderMapper;
import com.llmquality.baseline.repository.OrderRepository;
import com.llmquality.baseline.repository.ProductRepository;
import com.llmquality.baseline.repository.UserRepository;
import com.llmquality.baseline.service.interfaces.OrderService;
import jakarta.transaction.Transactional;
import org.slf4j.LoggerFactory;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.util.UUID;


@Service
public class OrderServiceImpl implements OrderService {

    private static final org.slf4j.Logger LOG = LoggerFactory.getLogger(OrderServiceImpl.class);

    private static final String ORDER = "Order";

    private static final String USER = "User";

    private static final String PRODUCT = "Product";

    private final OrderRepository orderRepository;

    private final ProductRepository productRepository;

    private final UserRepository userRepository;

    private final OrderMapper orderMapper;


    public OrderServiceImpl(final OrderRepository orderRepository,
                            final ProductRepository productRepository,
                            final UserRepository userRepository,
                            final OrderMapper orderMapper) {
        this.orderRepository = orderRepository;
        this.productRepository = productRepository;
        this.userRepository = userRepository;
        this.orderMapper = orderMapper;
    }

    @Override
    public PagedResponse<OrderResponse> listAll(Pageable pageable) {
        LOG.debug("--> listAll orders");
        Page<OrderResponse> page = orderRepository.findAll(pageable).map(orderMapper::toResponse);
        return PagedResponse.fromPage(page);
    }

    @Override
    public OrderResponse getById(Long id) {
        LOG.debug("--> getById order {}", id);
        Order order = orderRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException(ORDER, "id", id));
        return orderMapper.toResponse(order);
    }

    @Override
    public OrderResponse save(OrderRequest request) {
        LOG.debug("--> save, new order with {} items", request.items().size());

        final String currentUsername = getCurrentUsername();
        final User user = userRepository.findByUsername(currentUsername)
                .orElseThrow(() -> {
                    LOG.error("<-- save, user '{}' not found", currentUsername);
                    return new ResourceNotFoundException(USER, "username", currentUsername);
                });

        Order order = new Order();
        order.setUser(user);
        order.setOrderNumber("ORD-" + UUID.randomUUID().toString().substring(0, 8).toUpperCase());
        order.setStatus(OrderStatus.PENDING);
        order.setTotalAmount(BigDecimal.ZERO);

        BigDecimal total = BigDecimal.ZERO;

        for (OrderItemRequest itemReq : request.items()) {
            Product product = productRepository.findById(itemReq.productId())
                    .orElseThrow(() -> new ResourceNotFoundException(PRODUCT, "id", itemReq.productId()));

            if (product.getStock() < itemReq.quantity()) {
                throw new IllegalArgumentException("Nicht genug Lagerbestand für Produkt: " + product.getTitle());
            }

            OrderItem item = new OrderItem();
            item.setOrder(order);
            item.setProduct(product);
            item.setQuantity(itemReq.quantity());
            item.setUnitPrice(product.getPrice());

            product.setStock(product.getStock() - itemReq.quantity());
            productRepository.save(product);

            order.addItem(item);
            total = total.add(product.getPrice().multiply(BigDecimal.valueOf(itemReq.quantity())));
        }

        order.setTotalAmount(total);
        final Order saved = orderRepository.save(order);
        final OrderResponse orderResponse = orderMapper.toResponse(saved);

        LOG.debug("<-- order created with id {} for user {} (total {})", saved.getId(), currentUsername, total);
        return orderResponse;
    }

    @Override
    public OrderResponse update(Long id, OrderRequest request) {
        throw new UnsupportedOperationException("Bestellungen können nach Erstellung nicht mehr geändert werden");
    }

    @Override
    @Transactional
    public void delete(Long id) {
        LOG.debug("--> delete order {}", id);
        Order order = orderRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException(ORDER, "id", id));

        // Lager zurückbuchen
        for (OrderItem item : order.getItems()) {
            Product p = item.getProduct();
            p.setStock(p.getStock() + item.getQuantity());
            productRepository.save(p);
        }

        orderRepository.delete(order);
    }

    public static String getCurrentUsername() {
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();

        if (auth == null || !auth.isAuthenticated() || auth.getPrincipal() == null) {
            throw new IllegalStateException("Kein authentifizierter Benutzer");
        }

        if (auth.getPrincipal() instanceof Jwt jwt) {
            return jwt.getSubject();
        }

        String name = auth.getName();
        return "anonymousUser".equals(name) ? null : name;
    }
}