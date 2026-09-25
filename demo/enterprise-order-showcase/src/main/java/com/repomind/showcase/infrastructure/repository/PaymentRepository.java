package com.repomind.showcase.infrastructure.repository;
import com.repomind.showcase.domain.payment.Payment;
public interface PaymentRepository {
    void save(Payment payment);
    Payment findByOrderId(String orderId);
}
