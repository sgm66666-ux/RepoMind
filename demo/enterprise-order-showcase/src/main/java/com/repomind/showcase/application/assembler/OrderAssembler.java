package com.repomind.showcase.application.assembler;
import com.repomind.showcase.api.request.OrderItemRequest;
import com.repomind.showcase.api.response.OrderResponse;
import com.repomind.showcase.application.command.PlaceOrderCommand;
import com.repomind.showcase.domain.order.Order;
import com.repomind.showcase.domain.order.OrderItem;
import com.repomind.showcase.domain.product.Product;
import com.repomind.showcase.domain.product.ProductService;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
public final class OrderAssembler {
    private final ProductService products;
    public OrderAssembler(ProductService products) { this.products = products; }
    public Order toOrder(PlaceOrderCommand command) {
        List<OrderItem> items = new ArrayList<>();
        for (OrderItemRequest line : command.getLines()) {
            Product product = products.loadProduct(line.getSku());
            items.add(new OrderItem(product, line.getQuantity()));
        }
        return new Order(UUID.randomUUID().toString(), command.getCustomerId(), items);
    }
    public OrderResponse toResponse(Order order) {
        return new OrderResponse(order.getId(), order.getStatus(), order.getTotal().toString(), order.getShipmentId());
    }
}
