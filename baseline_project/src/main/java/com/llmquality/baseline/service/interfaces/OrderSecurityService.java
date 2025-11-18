package com.llmquality.baseline.service.interfaces;


public interface OrderSecurityService {

    boolean isOrderOwner(Long orderId);

    boolean isAdmin();

    Long getCurrentUserId();
}
