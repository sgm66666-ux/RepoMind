package com.repomind.showcase.application.service;
import com.repomind.showcase.api.request.CreateOrderRequest;
import com.repomind.showcase.api.response.OrderResponse;
import com.repomind.showcase.application.assembler.OrderAssembler;
import com.repomind.showcase.application.command.PlaceOrderCommand;
import com.repomind.showcase.domain.order.Order;
import com.repomind.showcase.domain.order.OrderService;
public final class OrderApplicationService {
    private final OrderAssembler assembler;
    private final OrderService orders;
    public OrderApplicationService(OrderAssembler assembler, OrderService orders) {
        this.assembler = assembler; this.orders = orders;
    }
    public OrderResponse createOrder(CreateOrderRequest request) {
        PlaceOrderCommand command = new PlaceOrderCommand(
            request.getCustomerId(), request.getItems(), request.getPayment().getMethod());
        Order order = assembler.toOrder(command);
        Order confirmed = orders.processOrder(order, command.getPaymentMethod());
        return assembler.toResponse(confirmed);
    }
}
