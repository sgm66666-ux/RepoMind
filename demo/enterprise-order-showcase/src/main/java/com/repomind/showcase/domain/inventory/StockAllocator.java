package com.repomind.showcase.domain.inventory;
import com.repomind.showcase.common.exception.InventoryException;
import com.repomind.showcase.infrastructure.repository.InventoryRepository;
public final class StockAllocator {
    private final InventoryRepository repository;
    public StockAllocator(InventoryRepository repository) { this.repository = repository; }
    public void allocate(String sku, int quantity) {
        Stock stock = repository.findAvailableStock(sku);
        if (stock.getAvailableQuantity() < quantity) throw new InventoryException("insufficient stock for " + sku);
        stock.reserve(quantity);
    }
}
