package com.llmquality.baseline.service;

import com.llmquality.baseline.repository.OrderRepository;
import com.llmquality.baseline.security.AuthenticationFacade;
import com.llmquality.baseline.service.interfaces.OrderSecurityService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

@Service("orderSecurityService")
public class OrderSecurityServiceImpl implements OrderSecurityService {

    private final AuthenticationFacade authenticationFacade;
    private final OrderRepository orderRepository;

    @Autowired
    public OrderSecurityServiceImpl(AuthenticationFacade authenticationFacade,  OrderRepository orderRepository) {
        this.authenticationFacade = authenticationFacade;
        this.orderRepository = orderRepository;
    }

    @Override
    public boolean isOrderOwner(Long orderId) {
        try {
            Long currentUserId = authenticationFacade.getCurrentUserId();
            if (currentUserId == null) {
                return false;
            }

            return orderRepository.findById(orderId)
                    .map(order -> order.getUser().getId().equals(currentUserId))
                    .orElse(false);

        } catch (Exception e) {
            // Bei jedem Fehler (z. B. JWT kaputt) sicher ablehnen
            return false;
        }
    }

    public boolean isAdmin() {
        return authenticationFacade.isAdmin();
    }

    public Long getCurrentUserId() {
        return authenticationFacade.getCurrentUserId();
    }
}
