package com.llmquality.baseline.service;

import com.llmquality.baseline.dto.order.*;
import com.llmquality.baseline.dto.user.PagedResponse;
import com.llmquality.baseline.entity.*;
import com.llmquality.baseline.enums.OrderStatus;
import com.llmquality.baseline.exception.AuthenticationRequiredException;
import com.llmquality.baseline.exception.ResourceNotFoundException;
import com.llmquality.baseline.mapper.OrderItemMapper;
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

    private final OrderItemMapper orderItemMapper;


    public OrderServiceImpl(final OrderRepository orderRepository,
                            final ProductRepository productRepository,
                            final UserRepository userRepository,
                            final OrderMapper orderMapper,
                            final OrderItemMapper orderItemMapper) {
        this.orderRepository = orderRepository;
        this.productRepository = productRepository;
        this.userRepository = userRepository;
        this.orderMapper = orderMapper;
        this.orderItemMapper = orderItemMapper;
    }

    @Override
    public PagedResponse<OrderResponse> listAll(Pageable pageable) {
        LOG.debug("--> listAll, page={}, size={}", pageable.getPageNumber(), pageable.getPageSize());
        final Page<OrderResponse> page = orderRepository.findAll(pageable).map(orderMapper::toOrderResponse);
        LOG.debug("<-- listAll, total elements={}, total pages={}", page.getTotalElements(), page.getTotalPages());
        return PagedResponse.fromPage(page);
    }

    @Override
    public OrderResponse getById(Long id) {
        LOG.debug("--> getById, order {}", id);
        final Order order = orderRepository.findById(id)
                .orElseThrow(() -> {
                    LOG.error("<-- getById, Order with ID {} not found", id);
                    return new ResourceNotFoundException(ORDER, "id", id);
                });
        final OrderResponse orderResponse = orderMapper.toOrderResponse(order);
        LOG.debug("<-- getById, order found: {}", orderResponse.id());
        return orderResponse;
    }

    @Transactional
    @Override
    public OrderResponse save(OrderRequest request) {
        LOG.debug("--> save, new order with {} items", request.items().size());

        final String currentUsername = getCurrentUsername();
        final User user = userRepository.findByUsername(currentUsername)
                .orElseThrow(() -> {
                    LOG.error("<-- save, user '{}' not found", currentUsername);
                    return new ResourceNotFoundException(USER, "username", currentUsername);
                });

        final Order order = orderMapper.toOrderEntity(request);
        order.setUser(user);
        order.setOrderNumber(generateUniqueOrderNumber());
        order.setStatus(OrderStatus.PENDING);
        order.setTotalAmount(BigDecimal.ZERO);

        BigDecimal total = BigDecimal.ZERO;

        for (OrderItemRequest itemReq : request.items()) {
            final Product product = productRepository.findById(itemReq.productId())
                    .orElseThrow(() -> new ResourceNotFoundException(PRODUCT, "id", itemReq.productId()));

            if (product.getStock() < itemReq.quantity()) {
                throw new IllegalArgumentException("Nicht genug Lagerbestand für Produkt: " + product.getTitle());
            }

            final OrderItem item = orderItemMapper.toOrderItemEntity(itemReq);
            item.setOrder(order);
            item.setProduct(product);
            item.setUnitPrice(product.getPrice());

            product.setStock(product.getStock() - itemReq.quantity());
            productRepository.save(product);

            order.addItem(item);
            total = total.add(product.getPrice().multiply(BigDecimal.valueOf(itemReq.quantity())));
        }

        order.setTotalAmount(total);
        final Order saved = orderRepository.save(order);
        final OrderResponse orderResponse = orderMapper.toOrderResponse(saved);

        LOG.debug("<-- order created with id {} for user {} (total {})", saved.getId(), currentUsername, total);
        return orderResponse;
    }

    @Override
    public OrderResponse update(Long id, OrderRequest request) {
        throw new UnsupportedOperationException("Bestellungen können nach Erstellung nicht mehr geändert werden");
    }

    @Override
    @Transactional
    public void delete(final Long id) {
        LOG.debug("--> delete, order with id {}", id);
        final Order order = orderRepository.findById(id)
                .orElseThrow(() -> {
                    LOG.error("<-- delete, id '{}' not found", id);
                    return new ResourceNotFoundException(ORDER, "id", id);
                });

        for (OrderItem item : order.getItems()) {
            final Product product = item.getProduct();
            product.setStock(product.getStock() + item.getQuantity());
            productRepository.save(product);
        }

        orderRepository.delete(order);
        LOG.debug("<-- delete, order with id: {}", id);
    }

    /**
     * Returns the username of the currently authenticated user.
     * <p>
     * Supports both JWT-based authentication (extracts the subject claim) and traditional
     * username-based authentication. Anonymous or unauthenticated requests result in an
     * {@link AuthenticationRequiredException}.
     * </p>
     *
     * @return the authenticated username (never {@code null}, blank or "anonymousUser")
     * @throws AuthenticationRequiredException if no valid authenticated user is present
     */
    public static String getCurrentUsername() {
        LOG.debug("--> getCurrentUsername");

        final Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth == null || !auth.isAuthenticated() || !(auth.getPrincipal() instanceof Jwt || auth.getPrincipal() instanceof String)) {
            LOG.debug("<-- getCurrentUsername, no valid authentication");
            throw new AuthenticationRequiredException(USER, "authentication", "none");
        }

        final String username = auth.getPrincipal() instanceof Jwt jwt ? jwt.getSubject() : auth.getName();

        if (username == null || username.isBlank() || "anonymousUser".equals(username)) {
            throw new AuthenticationRequiredException(USER, "authentication", "anonymous");
        }

        LOG.debug("<-- getCurrentUsername, {}", username);
        return username;
    }

    /**
     * Generates a unique order number in format {@code ORD-XXXXXXXX}.
     * Continuously generates candidates until a non-existing one is found in the database.
     * Collisions are extremely rare but handled safely via retry.
     *
     * @return a guaranteed unique order number
     */
    private String generateUniqueOrderNumber() {
        LOG.debug("--> generateUniqueOrderNumber");
        String candidate;

        while (orderRepository.existsByOrderNumber(candidate = generateCandidate())) {
            LOG.warn("Order number collision detected: {} → generating a new one", candidate);
        }

        LOG.debug("<-- generateUniqueOrderNumber, Unique order number generated: {}", candidate);
        return candidate;
    }

    /**
     * Generates a single candidate order number in the format {@code ORD-XXXXXXXX}
     * using the first 8 characters of a random UUID (uppercase, no hyphens).
     *
     * @return a raw order number candidate, e.g. {@code ORD-A1B2C3D4}
     */
    private static String generateCandidate() {
        LOG.debug("--> generateCandidate");
        final String candidate = "ORD-" + UUID.randomUUID()
                .toString()
                .replace("-", "")
                .substring(0, 8)
                .toUpperCase();
        LOG.debug("<-- generateCandidate, Order number candidate generated: {}", candidate);
        return candidate;
    }
}