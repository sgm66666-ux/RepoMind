package com.repomind.showcase.infrastructure.shipment;
import com.repomind.showcase.domain.customer.Address;
import com.repomind.showcase.domain.shipment.Shipment;
import com.repomind.showcase.domain.shipment.ShippingProvider;
public final class LocalShippingProvider implements ShippingProvider {
    @Override public Shipment book(String orderId, Address address) {
        return new Shipment("LOCAL-" + orderId, address);
    }
}
