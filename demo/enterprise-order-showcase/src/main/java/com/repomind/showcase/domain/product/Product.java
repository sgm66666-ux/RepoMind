package com.repomind.showcase.domain.product;
import com.repomind.showcase.domain.pricing.Money;
public final class Product {
    private final String sku;
    private final String name;
    private final Money price;
    private final boolean active;
    public Product(String sku, String name, Money price, boolean active) {
        this.sku = sku; this.name = name; this.price = price; this.active = active;
    }
    public String getSku() { return sku; }
    public String getName() { return name; }
    public Money getPrice() { return price; }
    public boolean isActive() { return active; }
}
