package demo.order;

public class OrderService {
    private final InventoryService inventoryService;

    public OrderService(InventoryService inventoryService) {
        this.inventoryService = inventoryService;
    }

    public void createOrder() {
        inventoryService.checkStock();
    }
}
