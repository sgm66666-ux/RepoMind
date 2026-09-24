public class OrderService {

    private PriceService priceService;

    public double createOrder() {
        return priceService.calculatePrice(100, 3);
    }
}
