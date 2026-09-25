package com.repomind.showcase.infrastructure.repository;
import com.repomind.showcase.domain.pricing.Promotion;
import java.util.HashMap;
import java.util.Map;
public final class InMemoryPromotionRepository implements PromotionRepository {
    private final Map<String, Promotion> promotions = new HashMap<>();
    public void assign(String customerId, Promotion promotion) { promotions.put(customerId, promotion); }
    @Override public Promotion findActiveFor(String customerId) { return promotions.get(customerId); }
}
