package com.repomind.showcase.infrastructure.repository;
import com.repomind.showcase.domain.product.Product;
import java.util.HashMap;
import java.util.Map;
public final class InMemoryProductRepository implements ProductRepository {
    private final Map<String, Product> products = new HashMap<>();
    public void add(Product product) { products.put(product.getSku(), product); }
    @Override public Product findBySku(String sku) { return products.get(sku); }
}
