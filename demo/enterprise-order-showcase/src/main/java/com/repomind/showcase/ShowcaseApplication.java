package com.repomind.showcase;
import com.repomind.showcase.api.controller.OrderController;
import com.repomind.showcase.api.request.CreateOrderRequest;
import com.repomind.showcase.api.request.OrderItemRequest;
import com.repomind.showcase.api.request.PaymentRequest;
import com.repomind.showcase.application.assembler.OrderAssembler;
import com.repomind.showcase.application.service.OrderApplicationService;
import com.repomind.showcase.domain.customer.Address;
import com.repomind.showcase.domain.customer.Customer;
import com.repomind.showcase.domain.customer.CustomerService;
import com.repomind.showcase.domain.inventory.InventoryService;
import com.repomind.showcase.domain.inventory.Stock;
import com.repomind.showcase.domain.inventory.StockAllocator;
import com.repomind.showcase.domain.notification.NotificationService;
import com.repomind.showcase.domain.notification.TemplateService;
import com.repomind.showcase.domain.order.OrderService;
import com.repomind.showcase.domain.payment.PaymentService;
import com.repomind.showcase.domain.pricing.*;
import com.repomind.showcase.domain.product.Product;
import com.repomind.showcase.domain.product.ProductService;
import com.repomind.showcase.domain.shipment.ShipmentService;
import com.repomind.showcase.infrastructure.audit.AuditService;
import com.repomind.showcase.infrastructure.notification.*;
import com.repomind.showcase.infrastructure.payment.*;
import com.repomind.showcase.infrastructure.repository.*;
import com.repomind.showcase.infrastructure.shipment.LocalShippingProvider;
import java.math.BigDecimal;
import java.util.List;
public final class ShowcaseApplication {
    private ShowcaseApplication() {}
    public static OrderController createController() {
        InMemoryProductRepository products = new InMemoryProductRepository();
        products.add(new Product("SKU-100", "Desk lamp", Money.of("29.90"), true));
        products.add(new Product("SKU-200", "USB hub", Money.of("39.00"), true));
        InMemoryCustomerRepository customers = new InMemoryCustomerRepository();
        customers.add(new Customer("C-100", "customer@example.test", true, false, new Address("Shanghai", "Market Road 8")));
        InMemoryInventoryRepository stock = new InMemoryInventoryRepository();
        stock.add(new Stock("SKU-100", 20));
        InMemoryPromotionRepository promotions = new InMemoryPromotionRepository();
        promotions.assign("C-100", new Promotion("SEASONAL", new BigDecimal("0.90")));
        ProductService productService = new ProductService(products);
        CustomerService customerService = new CustomerService(customers);
        PromotionService promotionService = new PromotionService(promotions);
        PricingService pricingService = new PricingService(new MemberDiscountPolicy(), new PromotionDiscountPolicy(promotionService));
        InventoryService inventoryService = new InventoryService(new StockAllocator(stock));
        PaymentService paymentService = new PaymentService(new MockBankPaymentGateway(), new WalletPaymentGateway(), new InMemoryPaymentRepository());
        ShipmentService shipmentService = new ShipmentService(new LocalShippingProvider());
        NotificationService notificationService = new NotificationService(new TemplateService(), new EmailNotificationSender(), new SmsNotificationSender());
        OrderService orderService = new OrderService(customerService, pricingService, inventoryService, paymentService,
            shipmentService, notificationService, new AuditService(), new InMemoryOrderRepository());
        OrderAssembler assembler = new OrderAssembler(productService);
        return new OrderController(new OrderApplicationService(assembler, orderService));
    }
    public static void main(String[] args) {
        CreateOrderRequest request = new CreateOrderRequest("C-100",
            List.of(new OrderItemRequest("SKU-100", 2)), new PaymentRequest("BANK"));
        System.out.println(createController().createOrder(request).getStatus());
    }
}
