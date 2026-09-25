package com.repomind.showcase.infrastructure.repository;
import com.repomind.showcase.domain.order.Order;
import java.util.HashMap;
import java.util.Map;
public final class InMemoryOrderRepository implements OrderRepository {
    private final Map<String, Order> orders = new HashMap<>();
    @Override public void save(Order order) { orders.put(order.getId(), order); }
    @Override public Order findById(String id) { return orders.get(id); }
}
