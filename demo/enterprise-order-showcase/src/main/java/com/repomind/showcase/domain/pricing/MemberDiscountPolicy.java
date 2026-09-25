package com.repomind.showcase.domain.pricing;
import com.repomind.showcase.domain.customer.Customer;
import java.math.BigDecimal;
public final class MemberDiscountPolicy implements DiscountPolicy {
    @Override public Money apply(Money subtotal, Customer customer) {
        if (customer.isMember()) return subtotal.multiply(new BigDecimal("0.95"));
        return subtotal;
    }
}
