package com.repomind.showcase.domain.pricing;
import com.repomind.showcase.domain.customer.Customer;
import com.repomind.showcase.domain.order.Order;
import com.repomind.showcase.domain.order.OrderItem;
public final class PricingService {
    private final MemberDiscountPolicy memberDiscount;
    private final PromotionDiscountPolicy promotionDiscount;
    public PricingService(MemberDiscountPolicy memberDiscount, PromotionDiscountPolicy promotionDiscount) {
        this.memberDiscount = memberDiscount; this.promotionDiscount = promotionDiscount;
    }
    public Money calculateOrderPrice(Order order, Customer customer) {
        Money subtotal = Money.of("0");
        for (OrderItem item : order.getItems()) subtotal = subtotal.add(item.lineTotal());
        Money adjusted = memberDiscount.apply(subtotal, customer);
        return promotionDiscount.apply(adjusted, customer).add(Money.of("4.99"));
    }
}
