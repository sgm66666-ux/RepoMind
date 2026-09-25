package com.repomind.showcase.domain.notification;
import com.repomind.showcase.domain.order.Order;
public final class TemplateService {
    public String orderConfirmation(Order order) {
        return "Order " + order.getId() + " confirmed, total " + order.getTotal();
    }
}
