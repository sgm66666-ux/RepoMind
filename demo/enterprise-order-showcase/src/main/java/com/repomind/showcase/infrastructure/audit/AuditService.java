package com.repomind.showcase.infrastructure.audit;
import com.repomind.showcase.domain.order.Order;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
public final class AuditService {
    private final List<AuditRecord> records = new ArrayList<>();
    public void recordOrderCreated(Order order) {
        records.add(new AuditRecord(order.getId(), "ORDER_CONFIRMED", Instant.now()));
    }
    public List<AuditRecord> historyFor(String orderId) {
        return records.stream().filter(record -> record.getOrderId().equals(orderId)).toList();
    }
}
