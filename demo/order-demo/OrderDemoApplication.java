package demo.order;

public class OrderDemoApplication {
    public static void main(String[] args) {
        InventoryRepository repository = new InventoryRepository();
        InventoryService inventoryService = new InventoryService(repository);
        OrderService orderService = new OrderService(inventoryService);
        OrderController controller = new OrderController(orderService);
        controller.createOrder();
    }
}
