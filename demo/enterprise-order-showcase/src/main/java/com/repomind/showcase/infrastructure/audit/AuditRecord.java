package com.repomind.showcase.infrastructure.audit;
import java.time.Instant;
public final class AuditRecord {
    private final String orderId;
    private final String action;
    private final Instant occurredAt;
    public AuditRecord(String orderId, String action, Instant occurredAt) {
        this.orderId = orderId; this.action = action; this.occurredAt = occurredAt;
    }
    public String getOrderId() { return orderId; }
    public String getAction() { return action; }
    public Instant getOccurredAt() { return occurredAt; }
}
