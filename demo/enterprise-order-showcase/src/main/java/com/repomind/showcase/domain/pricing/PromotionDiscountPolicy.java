package com.repomind.showcase.domain.pricing;
import com.repomind.showcase.domain.customer.Customer;
public final class PromotionDiscountPolicy implements DiscountPolicy {
    private final PromotionService promotions;
    public PromotionDiscountPolicy(PromotionService promotions) { this.promotions = promotions; }
    @Override public Money apply(Money subtotal, Customer customer) {
        Promotion promotion = promotions.activeFor(customer.getId());
        return promotion == null ? subtotal : subtotal.multiply(promotion.getMultiplier());
    }
}
