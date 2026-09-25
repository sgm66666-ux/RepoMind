package com.repomind.showcase.domain.notification;
import com.repomind.showcase.domain.customer.Customer;
import com.repomind.showcase.domain.order.Order;
import com.repomind.showcase.infrastructure.notification.EmailNotificationSender;
import com.repomind.showcase.infrastructure.notification.SmsNotificationSender;
public final class NotificationService {
    private final TemplateService templates;
    private final EmailNotificationSender email;
    private final SmsNotificationSender sms;
    public NotificationService(TemplateService templates, EmailNotificationSender email, SmsNotificationSender sms) {
        this.templates = templates; this.email = email; this.sms = sms;
    }
    public void sendOrderConfirmation(Order order, Customer customer) {
        String message = templates.orderConfirmation(order);
        if (customer.isSmsPreferred()) sms.send(customer, message);
        else email.send(customer, message);
    }
}
