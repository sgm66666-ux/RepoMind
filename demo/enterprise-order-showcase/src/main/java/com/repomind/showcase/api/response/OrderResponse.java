package com.repomind.showcase.api.response;
public final class OrderResponse {
    private final String orderId;
    private final String status;
    private final String total;
    private final String shipmentId;
    public OrderResponse(String orderId, String status, String total, String shipmentId) {
        this.orderId = orderId; this.status = status; this.total = total; this.shipmentId = shipmentId;
    }
    public String getOrderId() { return orderId; }
    public String getStatus() { return status; }
    public String getTotal() { return total; }
    public String getShipmentId() { return shipmentId; }
}
