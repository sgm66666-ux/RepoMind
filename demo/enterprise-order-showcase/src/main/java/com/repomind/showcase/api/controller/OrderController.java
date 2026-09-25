package com.repomind.showcase.api.controller;
import com.repomind.showcase.api.request.CreateOrderRequest;
import com.repomind.showcase.api.response.OrderResponse;
import com.repomind.showcase.application.service.OrderApplicationService;
public final class OrderController {
    private final OrderApplicationService application;
    public OrderController(OrderApplicationService application) { this.application = application; }
    public OrderResponse createOrder(CreateOrderRequest request) { return application.createOrder(request); }
}
