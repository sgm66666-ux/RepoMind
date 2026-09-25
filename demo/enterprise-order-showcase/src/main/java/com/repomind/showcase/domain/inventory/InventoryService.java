package com.repomind.showcase.domain.inventory;
import com.repomind.showcase.domain.order.Order;
import com.repomind.showcase.domain.order.OrderItem;
public final class InventoryService {
    private final StockAllocator allocator;
    public InventoryService(StockAllocator allocator) { this.allocator = allocator; }
    public void reserveInventory(Order order) {
        for (OrderItem item : order.getItems()) {
            allocator.allocate(item.getProduct().getSku(), item.getQuantity());
        }
    }
}
