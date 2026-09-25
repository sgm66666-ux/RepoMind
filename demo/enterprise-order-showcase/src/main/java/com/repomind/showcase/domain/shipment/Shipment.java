package com.repomind.showcase.domain.shipment;
import com.repomind.showcase.domain.customer.Address;
public final class Shipment {
    private final String trackingId;
    private final Address destination;
    public Shipment(String trackingId, Address destination) { this.trackingId = trackingId; this.destination = destination; }
    public String getTrackingId() { return trackingId; }
    public Address getDestination() { return destination; }
}
