package demo.order;

public class InventoryService {
    private final InventoryRepository inventoryRepository;

    public InventoryService(InventoryRepository inventoryRepository) {
        this.inventoryRepository = inventoryRepository;
    }

    public void checkStock() {
        Inventory stock = inventoryRepository.findStock();
        if (stock.available) {
            System.out.println("stock available");
        }
    }
}
