package com.repomind.showcase.api.request;
public final class OrderItemRequest {
    private final String sku;
    private final int quantity;
    public OrderItemRequest(String sku, int quantity) { this.sku = sku; this.quantity = quantity; }
    public String getSku() { return sku; }
    public int getQuantity() { return quantity; }
}
