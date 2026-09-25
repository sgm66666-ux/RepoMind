package com.repomind.showcase.domain.payment;
import com.repomind.showcase.domain.pricing.Money;
public final class Payment {
    private final String orderId;
    private final Money amount;
    private final String reference;
    public Payment(String orderId, Money amount, String reference) {
        this.orderId = orderId; this.amount = amount; this.reference = reference;
    }
    public String getOrderId() { return orderId; }
    public Money getAmount() { return amount; }
    public String getReference() { return reference; }
}
