package com.repomind.showcase.domain.pricing;
import com.repomind.showcase.infrastructure.repository.PromotionRepository;
public final class PromotionService {
    private final PromotionRepository repository;
    public PromotionService(PromotionRepository repository) { this.repository = repository; }
    public Promotion activeFor(String customerId) { return repository.findActiveFor(customerId); }
}
