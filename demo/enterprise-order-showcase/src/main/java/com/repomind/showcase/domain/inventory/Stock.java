package com.repomind.showcase.domain.inventory;
import com.repomind.showcase.common.exception.InventoryException;
public final class Stock {
    private final String sku;
    private int availableQuantity;
    public Stock(String sku, int availableQuantity) { this.sku = sku; this.availableQuantity = availableQuantity; }
    public String getSku() { return sku; }
    public int getAvailableQuantity() { return availableQuantity; }
    public void reserve(int quantity) {
        if (quantity <= 0 || quantity > availableQuantity) throw new InventoryException("insufficient stock for " + sku);
        availableQuantity -= quantity;
    }
}
