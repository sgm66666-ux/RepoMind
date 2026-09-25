package com.repomind.showcase.infrastructure.repository;
import com.repomind.showcase.domain.pricing.Promotion;
public interface PromotionRepository { Promotion findActiveFor(String customerId); }
