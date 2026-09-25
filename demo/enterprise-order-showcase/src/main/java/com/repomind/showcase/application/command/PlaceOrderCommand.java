package com.repomind.showcase.application.command;
import com.repomind.showcase.api.request.OrderItemRequest;
import java.util.List;
public final class PlaceOrderCommand {
    private final String customerId;
    private final List<OrderItemRequest> lines;
    private final String paymentMethod;
    public PlaceOrderCommand(String customerId, List<OrderItemRequest> lines, String paymentMethod) {
        this.customerId = customerId; this.lines = List.copyOf(lines); this.paymentMethod = paymentMethod;
    }
    public String getCustomerId() { return customerId; }
    public List<OrderItemRequest> getLines() { return lines; }
    public String getPaymentMethod() { return paymentMethod; }
}
