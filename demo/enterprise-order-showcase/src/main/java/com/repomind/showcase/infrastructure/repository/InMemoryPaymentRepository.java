package com.repomind.showcase.infrastructure.repository;
import com.repomind.showcase.domain.payment.Payment;
import java.util.HashMap;
import java.util.Map;
public final class InMemoryPaymentRepository implements PaymentRepository {
    private final Map<String, Payment> payments = new HashMap<>();
    @Override public void save(Payment payment) { payments.put(payment.getOrderId(), payment); }
    @Override public Payment findByOrderId(String orderId) { return payments.get(orderId); }
}
