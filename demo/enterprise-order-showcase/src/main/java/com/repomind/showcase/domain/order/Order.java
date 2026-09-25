package com.repomind.showcase.domain.order;
import com.repomind.showcase.domain.pricing.Money;
import java.util.List;
public final class Order {
    private final String id;
    private final String customerId;
    private final List<OrderItem> items;
    private Money total = Money.of("0");
    private String status = "CREATED";
    private String shipmentId;
    public Order(String id, String customerId, List<OrderItem> items) {
        if (items.isEmpty()) throw new IllegalArgumentException("order requires items");
        this.id = id; this.customerId = customerId; this.items = List.copyOf(items);
    }
    public String getId() { return id; }
    public String getCustomerId() { return customerId; }
    public List<OrderItem> getItems() { return items; }
    public Money getTotal() { return total; }
    public String getStatus() { return status; }
    public String getShipmentId() { return shipmentId; }
    public void setTotal(Money total) { this.total = total; }
    public void confirm() { status = "CONFIRMED"; }
    public void attachShipment(String shipmentId) { this.shipmentId = shipmentId; }
}
