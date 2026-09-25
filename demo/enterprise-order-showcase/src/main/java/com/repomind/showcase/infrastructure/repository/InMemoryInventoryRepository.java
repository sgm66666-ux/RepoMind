package com.repomind.showcase.infrastructure.repository;
import com.repomind.showcase.domain.inventory.Stock;
import java.util.HashMap;
import java.util.Map;
public final class InMemoryInventoryRepository implements InventoryRepository {
    private final Map<String, Stock> stockBySku = new HashMap<>();
    public void add(Stock stock) { stockBySku.put(stock.getSku(), stock); }
    @Override public Stock findAvailableStock(String sku) {
        Stock stock = stockBySku.get(sku);
        if (stock == null) return null;
        return stock;
    }
}
