package com.llmquality.baseline.enums;


/**
 * Enum representing the possible statuses of an order in the system.
 * Each status indicates the current state of an order in the order lifecycle.
 *
 * <p>
 * Available statuses:
 * <ul>
 *     <li>PENDING     - Order has been created but not yet confirmed</li>
 *     <li>CONFIRMED   - Order has been confirmed by the system or seller</li>
 *     <li>PAID        - Payment for the order has been completed</li>
 *     <li>PROCESSING  - Order is being prepared for shipment</li>
 *     <li>SHIPPED     - Order has been shipped to the customer</li>
 *     <li>COMPLETED   - Order has been delivered and finalized</li>
 *     <li>CANCELLED   - Order has been cancelled before completion</li>
 *     <li>REFUNDED    - Payment for the order has been refunded</li>
 * </ul>
 * </p>
 */
public enum OrderStatus {
    PENDING,
    CONFIRMED,
    PAID,
    PROCESSING,
    SHIPPED,
    COMPLETED,
    CANCELLED,
    REFUNDED
}
