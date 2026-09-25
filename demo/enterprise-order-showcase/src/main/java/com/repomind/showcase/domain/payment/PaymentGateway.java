package com.repomind.showcase.domain.payment;
import com.repomind.showcase.domain.pricing.Money;
public interface PaymentGateway { String charge(String customerId, Money amount); }
