package com.llmquality.baseline.service;

import com.llmquality.baseline.dto.order.*;
import com.llmquality.baseline.dto.user.PagedResponse;
import com.llmquality.baseline.entity.*;
import com.llmquality.baseline.enums.OrderStatus;
import com.llmquality.baseline.exception.ResourceNotFoundException;
import com.llmquality.baseline.mapper.OrderMapper;
import com.llmquality.baseline.repository.OrderRepository;
import com.llmquality.baseline.repository.ProductRepository;
import com.llmquality.baseline.service.interfaces.OrderService;
import jakarta.transaction.Transactional;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.util.UUID;

@Service
public class OrderServiceImpl implements OrderService {

    private static final org.slf4j.Logger LOG = LoggerFactory.getLogger(OrderServiceImpl.class);

    private static final String ORDER = "Order";

    private static final String PRODUCT = "Product";

    private final OrderRepository orderRepository;
    private final ProductRepository productRepository;
    private final OrderMapper orderMapper;
    private final ObjectProvider<Jwt> jwtProvider;

    public OrderServiceImpl(final OrderRepository orderRepository,
                            final ProductRepository productRepository,
                            final OrderMapper orderMapper,
                            final ObjectProvider<Jwt> jwtProvider) {
        this.orderRepository = orderRepository;
        this.productRepository = productRepository;
        this.orderMapper = orderMapper;
        this.jwtProvider = jwtProvider;
    }

    @Override
    public PagedResponse<OrderResponse> listAll(Pageable pageable) {
        LOG.debug("--> listAll orders");
        Page<OrderResponse> page = orderRepository.findAll(pageable)
                .map(orderMapper::toResponse);
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
        LOG.debug("--> create new order with {} items", request.items().size());

        // Saubere Trennung: Wer ist gerade angemeldet?
        Jwt jwt = jwtProvider.getIfAvailable();  // kann null sein (z. B. in Tests)

        String username = jwt != null
                ? jwt.getSubject()
                : "LOOL";
        LOG.error(username);


//
//        Order order = new Order();
//        order.setUser(username); // oder order.setUser(userRepository.findByUsername(username)... wenn du die Entity brauchst
//        order.setOrderNumber("ORD-" + UUID.randomUUID().toString().substring(0, 8).toUpperCase());
//        order.setStatus(OrderStatus.PENDING);
//        order.setTotalAmount(BigDecimal.ZERO);
//
//        BigDecimal total = BigDecimal.ZERO;
//
//        for (OrderItemRequest itemReq : request.items()) {
//            Product product = productRepository.findById(itemReq.productId())
//                    .orElseThrow(() -> new ResourceNotFoundException(PRODUCT, "id", itemReq.productId()));
//
//            if (product.getStock() < itemReq.quantity()) {
//                throw new IllegalArgumentException("Nicht genug Lagerbestand für Produkt: " + product.getTitle());
//            }
//
//            OrderItem item = new OrderItem();
//            item.setOrder(order);
//            item.setProduct(product);
//            item.setQuantity(itemReq.quantity());
//            item.setUnitPrice(product.getPrice());
//
//            // Lager reduzieren
//            product.setStock(product.getStock() - itemReq.quantity());
//            productRepository.save(product);
//
//            order.addItem(item);
//            total = total.add(product.getPrice().multiply(BigDecimal.valueOf(itemReq.quantity())));
//        }
//
//        order.setTotalAmount(total);
//        Order saved = orderRepository.save(order);
//
//        LOG.debug("<-- order created with id {} for user {} (total {})", saved.getId(), username, total);
        return null;
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

    public String getCurrentUsername() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();

        if (authentication != null && authentication.getPrincipal() instanceof Jwt jwt) {
            return jwt.getSubject();
        }

        return null;
    }

    /**
     * Wirft eine Exception, wenn kein authentifizierter User vorhanden ist
     */
    public String getCurrentUsernameRequired() {
        String username = getCurrentUsername();
        if (username == null) {
            throw new IllegalStateException("Kein authentifizierter Benutzer gefunden");
        }
        return username;
    }
}