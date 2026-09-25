package com.repomind.showcase.domain.shipment;
import com.repomind.showcase.domain.customer.Address;
public interface ShippingProvider { Shipment book(String orderId, Address address); }
