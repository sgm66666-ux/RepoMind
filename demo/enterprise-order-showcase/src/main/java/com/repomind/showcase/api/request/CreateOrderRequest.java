package com.repomind.showcase.api.request;
import java.util.List;
public final class CreateOrderRequest {
    private final String customerId;
    private final List<OrderItemRequest> items;
    private final PaymentRequest payment;
    public CreateOrderRequest(String customerId, List<OrderItemRequest> items, PaymentRequest payment) {
        this.customerId = customerId; this.items = List.copyOf(items); this.payment = payment;
    }
    public String getCustomerId() { return customerId; }
    public List<OrderItemRequest> getItems() { return items; }
    public PaymentRequest getPayment() { return payment; }
}
