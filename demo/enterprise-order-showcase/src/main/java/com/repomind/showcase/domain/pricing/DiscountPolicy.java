package com.repomind.showcase.domain.pricing;
import com.repomind.showcase.domain.customer.Customer;
public interface DiscountPolicy { Money apply(Money subtotal, Customer customer); }
