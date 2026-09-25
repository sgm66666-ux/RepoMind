package com.repomind.showcase.domain.notification;
import com.repomind.showcase.domain.customer.Customer;
public interface NotificationSender { void send(Customer customer, String message); }
