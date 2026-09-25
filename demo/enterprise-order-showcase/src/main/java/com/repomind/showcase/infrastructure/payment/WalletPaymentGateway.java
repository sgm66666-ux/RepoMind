package com.repomind.showcase.infrastructure.payment;
import com.repomind.showcase.common.exception.PaymentException;
import com.repomind.showcase.domain.payment.PaymentGateway;
import com.repomind.showcase.domain.pricing.Money;
public final class WalletPaymentGateway implements PaymentGateway {
    @Override public String charge(String customerId, Money amount) {
        if (amount.amount().signum() <= 0) throw new PaymentException("invalid wallet amount");
        return "WALLET-" + customerId + "-" + amount;
    }
}
