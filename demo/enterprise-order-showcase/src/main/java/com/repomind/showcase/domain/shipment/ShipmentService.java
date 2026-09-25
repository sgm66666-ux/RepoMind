package com.repomind.showcase.domain.shipment;
import com.repomind.showcase.domain.customer.Customer;
import com.repomind.showcase.domain.order.Order;
import com.repomind.showcase.infrastructure.shipment.LocalShippingProvider;
public final class ShipmentService {
    private final LocalShippingProvider provider;
    public ShipmentService(LocalShippingProvider provider) { this.provider = provider; }
    public Shipment createShipment(Order order, Customer customer) {
        Shipment shipment = provider.book(order.getId(), customer.getAddress());
        order.attachShipment(shipment.getTrackingId());
        return shipment;
    }
}
