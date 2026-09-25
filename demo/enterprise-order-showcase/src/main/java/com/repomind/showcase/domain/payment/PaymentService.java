package com.repomind.showcase.domain.payment;
import com.repomind.showcase.domain.order.Order;
import com.repomind.showcase.infrastructure.payment.MockBankPaymentGateway;
import com.repomind.showcase.infrastructure.payment.WalletPaymentGateway;
import com.repomind.showcase.infrastructure.repository.PaymentRepository;
public final class PaymentService {
    private final MockBankPaymentGateway bank;
    private final WalletPaymentGateway wallet;
    private final PaymentRepository repository;
    public PaymentService(MockBankPaymentGateway bank, WalletPaymentGateway wallet, PaymentRepository repository) {
        this.bank = bank; this.wallet = wallet; this.repository = repository;
    }
    public Payment pay(Order order, String method) {
        String reference = "WALLET".equals(method)
            ? wallet.charge(order.getCustomerId(), order.getTotal())
            : bank.charge(order.getCustomerId(), order.getTotal());
        Payment payment = new Payment(order.getId(), order.getTotal(), reference);
        repository.save(payment);
        return payment;
    }
}
