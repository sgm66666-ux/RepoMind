package com.repomind.showcase.infrastructure.notification;
import com.repomind.showcase.domain.customer.Customer;
import com.repomind.showcase.domain.notification.NotificationSender;
import java.util.ArrayList;
import java.util.List;
public final class SmsNotificationSender implements NotificationSender {
    private final List<String> outbox = new ArrayList<>();
    @Override public void send(Customer customer, String message) { outbox.add(customer.getId() + ": " + message); }
    public List<String> sentMessages() { return List.copyOf(outbox); }
}
