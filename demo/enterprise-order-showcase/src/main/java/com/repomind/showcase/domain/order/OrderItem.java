package com.repomind.showcase.domain.order;
import com.repomind.showcase.domain.pricing.Money;
import com.repomind.showcase.domain.product.Product;
import java.math.BigDecimal;
public final class OrderItem {
    private final Product product;
    private final int quantity;
    public OrderItem(Product product, int quantity) {
        if (quantity <= 0) throw new IllegalArgumentException("quantity must be positive");
        this.product = product; this.quantity = quantity;
    }
    public Product getProduct() { return product; }
    public int getQuantity() { return quantity; }
    public Money lineTotal() { return product.getPrice().multiply(BigDecimal.valueOf(quantity)); }
}
