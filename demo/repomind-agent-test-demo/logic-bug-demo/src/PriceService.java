public class PriceService {

    public double calculatePrice(double price, int quantity) {

        double discount = 0.8;

        // Bug: incorrect calculation
        return price + quantity * discount;
    }
}
