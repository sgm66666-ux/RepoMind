package com.repomind.showcase;
import com.repomind.showcase.api.request.CreateOrderRequest;
import com.repomind.showcase.api.request.OrderItemRequest;
import com.repomind.showcase.api.request.PaymentRequest;
import com.repomind.showcase.api.response.OrderResponse;
import com.repomind.showcase.domain.inventory.Stock;
import com.repomind.showcase.domain.inventory.StockAllocator;
import com.repomind.showcase.infrastructure.repository.InMemoryInventoryRepository;
import org.junit.jupiter.api.Test;
import java.util.List;
import static org.junit.jupiter.api.Assertions.*;
class OrderFlowTest {
    @Test void orderCreationCompletes() {
        CreateOrderRequest request = new CreateOrderRequest("C-100",
            List.of(new OrderItemRequest("SKU-100", 2)), new PaymentRequest("BANK"));
        OrderResponse response = ShowcaseApplication.createController().createOrder(request);
        assertEquals("CONFIRMED", response.getStatus());
        assertNotNull(response.getShipmentId());
        assertFalse(response.getTotal().isBlank());
    }
    @Test void walletPaymentAlsoCompletes() {
        CreateOrderRequest request = new CreateOrderRequest("C-100",
            List.of(new OrderItemRequest("SKU-100", 1)), new PaymentRequest("WALLET"));
        assertEquals("CONFIRMED", ShowcaseApplication.createController().createOrder(request).getStatus());
    }
    @Test void inventoryReservationReducesAvailableQuantity() {
        InMemoryInventoryRepository repository = new InMemoryInventoryRepository();
        Stock stock = new Stock("SKU-100", 10);
        repository.add(stock);
        new StockAllocator(repository).allocate("SKU-100", 3);
        assertEquals(7, stock.getAvailableQuantity());
    }
}
