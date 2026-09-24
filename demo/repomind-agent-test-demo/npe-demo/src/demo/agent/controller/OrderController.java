package demo.agent.controller;

import demo.agent.service.OrderService;

public class OrderController {
    private final OrderService orderService;

    public OrderController(OrderService orderService) {
        this.orderService = orderService;
    }

    public void createOrder(String userId) {
        orderService.createOrder(userId);
    }
}
