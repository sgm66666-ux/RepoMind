package com.repomind.showcase.infrastructure.repository;
import com.repomind.showcase.domain.order.Order;
public interface OrderRepository {
    void save(Order order);
    Order findById(String id);
}
