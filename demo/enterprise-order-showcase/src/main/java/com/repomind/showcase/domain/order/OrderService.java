package com.repomind.showcase.domain.order;
import com.repomind.showcase.domain.customer.Customer;
import com.repomind.showcase.domain.customer.CustomerService;
import com.repomind.showcase.domain.inventory.InventoryService;
import com.repomind.showcase.domain.notification.NotificationService;
import com.repomind.showcase.domain.payment.PaymentService;
import com.repomind.showcase.domain.pricing.Money;
import com.repomind.showcase.domain.pricing.PricingService;
import com.repomind.showcase.domain.shipment.ShipmentService;
import com.repomind.showcase.infrastructure.audit.AuditService;
import com.repomind.showcase.infrastructure.repository.OrderRepository;
public final class OrderService {
    private final CustomerService customers;
    private final PricingService pricing;
    private final InventoryService inventory;
    private final PaymentService payments;
    private final ShipmentService shipments;
    private final NotificationService notifications;
    private final AuditService audit;
    private final OrderRepository orders;
    public OrderService(CustomerService customers, PricingService pricing, InventoryService inventory,
                        PaymentService payments, ShipmentService shipments, NotificationService notifications,
                        AuditService audit, OrderRepository orders) {
        this.customers = customers; this.pricing = pricing; this.inventory = inventory;
        this.payments = payments; this.shipments = shipments; this.notifications = notifications;
        this.audit = audit; this.orders = orders;
    }
    public Order processOrder(Order order, String paymentMethod) {
        Customer customer = customers.validateCustomer(order.getCustomerId());
        Money total = pricing.calculateOrderPrice(order, customer);
        order.setTotal(total);
        inventory.reserveInventory(order);
        payments.pay(order, paymentMethod);
        order.confirm();
        shipments.createShipment(order, customer);
        notifications.sendOrderConfirmation(order, customer);
        audit.recordOrderCreated(order);
        orders.save(order);
        return order;
    }
}
